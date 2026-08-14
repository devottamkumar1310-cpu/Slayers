"""
Pipeline Worker — orchestrates the full SLAYERS processing pipeline.

Architecture:
  1. Content ingestion & analysis      → ContentAnalyzer
  2. Segment persistence               → ContentSegment rows
  3. Visual intent & requirements      → VisualIntentEngine + AssetRequirement rows
  4. Concurrent asset discovery        → AssetDiscoveryEngine + Asset rows
  5. Finalization                      → job.status = completed

Error isolation:
  - Segment-level failures do not abort the full pipeline
  - Fatal errors mark project/job as 'failed' with stored error message
  - DB session is always closed in finally block

Observability:
  - Every step updates job.current_step + job.progress
  - Provider stats written to job.provider_stats
  - Warnings accumulated in job.warnings
"""
from __future__ import annotations

import logging
import asyncio
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.models import Project, ContentSegment, AssetRequirement, Asset, ProcessingJob
from app.services.content_analyzer import ContentAnalyzer
from app.services.visual_intent import VisualIntentEngine
from app.services.asset_discovery import AssetDiscoveryEngine

logger = logging.getLogger("slayers.pipeline")


def _update_job(db: Session, job: ProcessingJob, step: str, progress: int) -> None:
    job.current_step = step
    job.progress = progress
    try:
        db.commit()
    except Exception as e:
        logger.warning("Failed to commit job progress update: %s", e)
        db.rollback()


async def process_project_pipeline(project_id: str) -> None:
    """Full async pipeline. Guaranteed to close its DB session."""
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        await _run_pipeline(db, project_id)
    except Exception as e:
        logger.exception("Unhandled fatal error in pipeline for project %s: %s", project_id, e)
        if db:
            _mark_failed(db, project_id, str(e))
    finally:
        if db:
            db.close()


async def _run_pipeline(db: Session, project_id: str) -> None:
    # ── Load project ─────────────────────────────────────────────────────────
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.error("Project %s not found — aborting pipeline", project_id)
        return

    # ── Initialize / reset job ────────────────────────────────────────────────
    job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
    if not job:
        job = ProcessingJob(project_id=project_id)
        db.add(job)

    job.status = "processing"
    job.current_step = "Pipeline initialized"
    job.progress = 5
    job.started_at = datetime.utcnow()
    job.error = None
    job.warnings = []
    job.provider_stats = {}
    project.status = "processing"
    db.commit()

    # ── STEP 1 — Content analysis (5 → 25%) ──────────────────────────────────
    _update_job(db, job, "Analyzing narrative structure", 10)
    analyzer = ContentAnalyzer()
    try:
        raw_segments = await analyzer.analyze(project.source_text)
    except Exception as e:
        raise RuntimeError(f"Content analysis failed: {e}") from e

    if not raw_segments:
        raise RuntimeError("Content analysis produced zero segments — check source text.")

    # ── STEP 2 — Persist segments (25 → 40%) ─────────────────────────────────
    _update_job(db, job, "Persisting content segments", 25)

    # Delete previous results (re-process support)
    db.query(ContentSegment).filter(ContentSegment.project_id == project_id).delete(synchronize_session=False)
    db.commit()

    created_segments: List[ContentSegment] = []
    for seg_data in raw_segments:
        seg = ContentSegment(
            project_id=project_id,
            sequence=seg_data.get("sequence", len(created_segments) + 1),
            start_time=seg_data.get("start_time", "00:00"),
            end_time=seg_data.get("end_time", "00:05"),
            text=seg_data.get("text", ""),
            scene_description=seg_data.get("scene_description", ""),
            visual_intent=seg_data.get("visual_intent", "stock_footage"),
            importance=seg_data.get("importance", "medium"),
        )
        db.add(seg)
        created_segments.append(seg)

    db.commit()
    logger.info("Persisted %d segments for project %s", len(created_segments), project_id)

    # ── STEP 3 — Visual intent + requirements (40 → 60%) ─────────────────────
    _update_job(db, job, "Generating visual requirements", 40)

    intent_engine = VisualIntentEngine()
    segment_req_pairs: List[tuple] = []
    segment_warnings: List[str] = []

    for segment in created_segments:
        try:
            seg_dict = {
                "text": segment.text,
                "visual_intent": segment.visual_intent,
                "scene_description": segment.scene_description,
            }
            reqs_data = await intent_engine.generate_requirements(seg_dict)

            for r_data in reqs_data:
                req = AssetRequirement(
                    segment_id=segment.id,
                    asset_type=r_data.get("asset_type", "stock_footage"),
                    description=r_data.get("description", "Visual asset required"),
                    search_query=r_data.get("search_query", "technology")[:500],
                    priority=r_data.get("priority", "medium"),
                    reason=r_data.get("reason", "Supports scene narration"),
                )
                db.add(req)
                segment_req_pairs.append((segment, req))
        except Exception as e:
            msg = f"Requirement generation failed for segment {segment.sequence}: {e}"
            logger.warning(msg)
            segment_warnings.append(msg)

    db.commit()
    logger.info("Generated %d requirements for project %s", len(segment_req_pairs), project_id)

    # ── STEP 4 — Asset discovery (60 → 90%) ──────────────────────────────────
    _update_job(db, job, "Discovering and ranking visual assets", 60)

    discovery_engine = AssetDiscoveryEngine()
    aggregated_stats: Dict[str, int] = defaultdict(int)
    total_pairs = len(segment_req_pairs)

    for idx, (segment, requirement) in enumerate(segment_req_pairs):
        # Incremental progress: 60 → 88
        prog = 60 + int(28 * (idx / max(total_pairs, 1)))
        if prog != job.progress:
            _update_job(db, job, f"Discovering assets ({idx + 1}/{total_pairs})", prog)

        try:
            req_dict = {
                "asset_type": requirement.asset_type,
                "search_query": requirement.search_query,
                "priority": requirement.priority,
            }
            assets_data, stats = await discovery_engine.discover_for_requirement(
                req_dict, segment.text
            )

            # Accumulate provider stats
            for provider_name, found_count in stats.get("found", {}).items():
                aggregated_stats[provider_name] += found_count

            # Collect warnings
            for w in stats.get("warnings", []):
                segment_warnings.append(w)

            for a_data in assets_data:
                asset = Asset(
                    requirement_id=requirement.id,
                    title=a_data["title"],
                    source=a_data["source"],
                    source_url=a_data["source_url"],
                    asset_url=a_data["asset_url"],
                    thumbnail_url=a_data["thumbnail_url"],
                    asset_type=a_data["asset_type"],
                    relevance_score=a_data["relevance_score"],
                    license_info=a_data["license_info"],
                    license_url=a_data.get("license_url"),
                    usage_notes=a_data["usage_notes"],
                    usage_status=a_data.get("usage_status", "verify_manually"),
                    status=a_data["status"],
                    provider_id=a_data.get("provider_id"),
                    metadata_json=a_data.get("metadata_json", {}),
                )
                db.add(asset)
        except Exception as e:
            msg = f"Asset discovery failed for requirement {requirement.id}: {e}"
            logger.error(msg, exc_info=True)
            segment_warnings.append(msg)

    db.commit()

    # ── STEP 5 — Finalization (90 → 100%) ─────────────────────────────────────
    job.current_step = "Visual Asset Package Ready"
    job.progress = 100
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    job.warnings = list(set(segment_warnings))[:50]   # deduplicate, cap at 50
    job.provider_stats = dict(aggregated_stats)
    project.status = "completed"
    db.commit()

    logger.info(
        "Pipeline complete for project %s | segments=%d, requirements=%d, stats=%s",
        project_id, len(created_segments), len(segment_req_pairs), dict(aggregated_stats)
    )


def _mark_failed(db: Session, project_id: str, error_msg: str) -> None:
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
        if job:
            job.status = "failed"
            job.error = error_msg[:2000]
            job.completed_at = datetime.utcnow()
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "failed"
        db.commit()
    except Exception as e:
        logger.error("Could not persist failure state for project %s: %s", project_id, e)
        try:
            db.rollback()
        except Exception:
            pass
