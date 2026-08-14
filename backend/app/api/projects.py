"""
Projects API — all project lifecycle endpoints.

Endpoints:
  POST   /projects              — create project
  GET    /projects              — list projects (paginated)
  GET    /projects/{id}         — get project detail
  DELETE /projects/{id}         — delete project
  POST   /projects/{id}/process — start / restart processing
  GET    /projects/{id}/status  — polling endpoint
  GET    /projects/{id}/segments
  GET    /projects/{id}/requirements
  GET    /projects/{id}/assets
  GET    /projects/{id}/summary
  POST   /projects/demo         — create and auto-process a demo project
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Asset, AssetRequirement, ContentSegment, ProcessingJob, Project
from app.schemas.schemas import (
    AssetRequirementResponse,
    AssetResponse,
    ContentSegmentResponse,
    ProcessingJobStatus,
    ProjectCreate,
    ProjectResponse,
    ProjectSummaryResponse,
)
from app.workers.pipeline_worker import process_project_pipeline

router = APIRouter(prefix="/projects", tags=["Projects"])

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=payload.name.strip(),
        source_type=payload.source_type,
        source_text=payload.source_text,
        status="draft",
    )
    db.add(project)
    db.flush()          # get project.id without committing

    job = ProcessingJob(
        project_id=project.id,
        status="pending",
        current_step="Created",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, project_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = _get_or_404(db, project_id)
    db.delete(project)
    db.commit()


# ── Processing ────────────────────────────────────────────────────────────────

@router.post("/{project_id}/process", response_model=ProcessingJobStatus)
def start_processing(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = _get_or_404(db, project_id)

    # Block re-run if already running
    job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
    if job and job.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="A processing job is already running for this project.",
        )

    if not job:
        job = ProcessingJob(project_id=project_id)
        db.add(job)

    job.status = "processing"
    job.current_step = "Starting pipeline"
    job.progress = 0
    job.started_at = datetime.utcnow()
    job.error = None
    job.warnings = None
    job.provider_stats = None
    project.status = "processing"
    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_project_pipeline, project_id)
    return job


@router.get("/{project_id}/status", response_model=ProcessingJobStatus)
def get_project_status(project_id: str, db: Session = Depends(get_db)):
    job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="No processing job found for this project.")
    return job


# ── Content access ────────────────────────────────────────────────────────────

@router.get("/{project_id}/segments", response_model=List[ContentSegmentResponse])
def get_segments(project_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, project_id)
    return (
        db.query(ContentSegment)
        .filter(ContentSegment.project_id == project_id)
        .order_by(ContentSegment.sequence)
        .all()
    )


@router.get("/{project_id}/requirements", response_model=List[AssetRequirementResponse])
def get_requirements(project_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, project_id)
    return (
        db.query(AssetRequirement)
        .join(ContentSegment, AssetRequirement.segment_id == ContentSegment.id)
        .filter(ContentSegment.project_id == project_id)
        .all()
    )


@router.get("/{project_id}/assets", response_model=List[AssetResponse])
def get_assets(project_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, project_id)
    return (
        db.query(Asset)
        .join(AssetRequirement, Asset.requirement_id == AssetRequirement.id)
        .join(ContentSegment, AssetRequirement.segment_id == ContentSegment.id)
        .filter(ContentSegment.project_id == project_id)
        .order_by(Asset.relevance_score.desc())
        .all()
    )


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
def get_summary(project_id: str, db: Session = Depends(get_db)):
    project = _get_or_404(db, project_id)

    segments = (
        db.query(ContentSegment)
        .filter(ContentSegment.project_id == project_id)
        .all()
    )
    requirements = (
        db.query(AssetRequirement)
        .join(ContentSegment)
        .filter(ContentSegment.project_id == project_id)
        .all()
    )
    assets = (
        db.query(Asset)
        .join(AssetRequirement)
        .join(ContentSegment)
        .filter(ContentSegment.project_id == project_id)
        .all()
    )

    high_conf = sum(1 for a in assets if a.relevance_score >= 80)
    needs_review = sum(1 for a in assets if a.status == "flagged" or a.usage_status == "verify_manually")

    source_counts: dict = {}
    for a in assets:
        source_counts[a.source] = source_counts.get(a.source, 0) + 1

    # Processing time
    actual_secs = 15
    job = project.processing_job
    if job and job.completed_at and job.started_at:
        delta = (job.completed_at - job.started_at).total_seconds()
        actual_secs = max(5, int(delta))

    return ProjectSummaryResponse(
        project_id=project_id,
        total_scenes=len(segments),
        total_requirements=len(requirements),
        total_assets=len(assets),
        high_confidence_matches=high_conf,
        needs_review=needs_review,
        total_sources=len(source_counts),
        provider_breakdown=source_counts,
        actual_processing_seconds=actual_secs,
        manual_estimate_minutes=len(requirements) * 5,
    )


# ── Demo ─────────────────────────────────────────────────────────────────────

_DEMO_SCRIPT = """\
The software industry is undergoing a massive shift as AI coding agents emerge.
Developers no longer spend hours writing boilerplate code manually.
Instead, intelligent agents analyze repositories, create implementation plans, and write multi-file features.
For example, modern IDE interfaces now feature AI pair-programmers integrated right into the editor window.
This transformation allows small engineering teams to build complex software in a fraction of the time.
Companies like GitHub, Google, and OpenAI are shipping AI tools that automate repetitive coding tasks.
The market data shows developer productivity increasing by 30 to 55 percent with AI-assisted workflows.
""".strip()


@router.post("/demo", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_demo_project(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Creates a sample project with realistic content and immediately starts processing."""
    project = Project(
        name="How AI Coding Agents Are Changing Software Development (Demo)",
        source_type="script",
        source_text=_DEMO_SCRIPT,
        status="draft",
    )
    db.add(project)
    db.flush()

    job = ProcessingJob(
        project_id=project.id,
        status="pending",
        current_step="Created",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(project)

    background_tasks.add_task(process_project_pipeline, project.id)
    return project
