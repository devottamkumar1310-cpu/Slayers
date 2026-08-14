import logging
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.models import Project, ContentSegment, AssetRequirement, Asset, ProcessingJob
from app.services.content_analyzer import ContentAnalyzer
from app.services.visual_intent import VisualIntentEngine
from app.services.asset_discovery import AssetDiscoveryEngine

logger = logging.getLogger("slayers.pipeline_worker")

async def process_project_pipeline(project_id: str):
    """Executes the async processing job pipeline for a project with robust per-step error isolation."""
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found")
            return

        job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
        if not job:
            job = ProcessingJob(
                project_id=project_id,
                status="processing",
                current_step="Pipeline Initialized",
                progress=5,
                started_at=datetime.utcnow()
            )
            db.add(job)
        else:
            job.status = "processing"
            job.current_step = "Pipeline Initialized"
            job.progress = 5
            job.started_at = datetime.utcnow()
            job.error = None
        
        project.status = "processing"
        db.commit()

        # Step 1: Content Ingestion & Analysis (Progress 15%)
        job.current_step = "Analyzing narrative beats and structure"
        job.progress = 15
        db.commit()
        await asyncio.sleep(0.3)

        analyzer = ContentAnalyzer()
        raw_segments = await analyzer.analyze(project.source_text)

        # Step 2: Content Segmentation (Progress 35%)
        job.current_step = "Segmenting script into timeline intervals"
        job.progress = 35
        db.commit()
        await asyncio.sleep(0.3)

        # Clean existing segments for re-processing
        db.query(ContentSegment).filter(ContentSegment.project_id == project_id).delete()
        db.commit()

        created_segments = []
        for seg_data in raw_segments:
            segment = ContentSegment(
                project_id=project_id,
                sequence=seg_data.get("sequence", 1),
                start_time=seg_data.get("start_time", "00:00"),
                end_time=seg_data.get("end_time", "00:05"),
                text=seg_data.get("text", ""),
                scene_description=seg_data.get("scene_description", ""),
                visual_intent=seg_data.get("visual_intent", "stock_footage"),
                importance=seg_data.get("importance", "medium")
            )
            db.add(segment)
            created_segments.append(segment)
        
        db.commit()

        # Step 3: Visual Intent Engine (Progress 55%)
        job.current_step = "Generating visual intent & asset requirements"
        job.progress = 55
        db.commit()
        await asyncio.sleep(0.3)

        intent_engine = VisualIntentEngine()
        segment_req_map = []

        for segment in created_segments:
            try:
                seg_dict = {
                    "text": segment.text,
                    "visual_intent": segment.visual_intent,
                    "scene_description": segment.scene_description
                }
                reqs_data = await intent_engine.generate_requirements(seg_dict)
                
                for r_data in reqs_data:
                    requirement = AssetRequirement(
                        segment_id=segment.id,
                        asset_type=r_data.get("asset_type", segment.visual_intent or "stock_footage"),
                        description=r_data.get("description", "Visual asset required"),
                        search_query=r_data.get("search_query", segment.visual_intent or "tech"),
                        priority=r_data.get("priority", "medium"),
                        reason=r_data.get("reason", "Supports scene narration")
                    )
                    db.add(requirement)
                    segment_req_map.append((segment, requirement))
            except Exception as seg_err:
                logger.error(f"Error generating requirement for segment {segment.id}: {seg_err}")
        
        db.commit()

        # Step 4: Asset Discovery & Relevance Scoring (Progress 80%)
        job.current_step = "Searching & ranking visual assets across providers"
        job.progress = 80
        db.commit()

        discovery_engine = AssetDiscoveryEngine()

        for segment, requirement in segment_req_map:
            try:
                req_dict = {
                    "asset_type": requirement.asset_type,
                    "search_query": requirement.search_query,
                    "priority": requirement.priority
                }
                assets_data = await discovery_engine.discover_for_requirement(req_dict, segment.text)
                
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
                        usage_notes=a_data["usage_notes"],
                        status=a_data["status"],
                        metadata_json=a_data["metadata_json"]
                    )
                    db.add(asset)
            except Exception as disc_err:
                logger.error(f"Error discovering assets for requirement {requirement.id}: {disc_err}")

        db.commit()

        # Step 5 & 6: Finalizing Asset Package (Progress 100%)
        job.current_step = "Visual Asset Package Ready"
        job.progress = 100
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        
        project.status = "completed"
        db.commit()
        logger.info(f"Successfully processed project {project_id}")

    except Exception as e:
        logger.exception(f"Fatal pipeline error for project {project_id}: {e}")
        if db:
            try:
                job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
                if job:
                    job.status = "failed"
                    job.error = str(e)
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = "failed"
                db.commit()
            except Exception as rollback_err:
                logger.error(f"Failed to record job failure: {rollback_err}")
                db.rollback()
    finally:
        if db:
            db.close()
