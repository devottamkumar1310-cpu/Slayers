from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.db import get_db
from app.models.models import Project, ContentSegment, AssetRequirement, Asset, ProcessingJob
from app.schemas.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectSummaryResponse,
    ContentSegmentResponse,
    AssetRequirementResponse,
    AssetResponse,
    ProcessingJobStatus
)
from app.workers.pipeline_worker import process_project_pipeline

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if not payload.source_text.strip():
        raise HTTPException(status_code=400, detail="Source text script cannot be empty.")
    
    project = Project(
        name=payload.name,
        source_type=payload.source_type,
        source_text=payload.source_text,
        status="draft"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    job = ProcessingJob(
        project_id=project.id,
        status="pending",
        current_step="Created",
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(project)

    return project

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project

@router.post("/{project_id}/process", response_model=ProcessingJobStatus)
def start_processing(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
    if not job:
        job = ProcessingJob(
            project_id=project_id,
            status="processing",
            current_step="Starting pipeline",
            progress=0,
            started_at=datetime.utcnow()
        )
        db.add(job)
    else:
        job.status = "processing"
        job.current_step = "Starting pipeline"
        job.progress = 0
        job.started_at = datetime.utcnow()
        job.error = None

    project.status = "processing"
    db.commit()
    db.refresh(job)

    # Launch background job
    background_tasks.add_task(process_project_pipeline, project_id)

    return job

@router.get("/{project_id}/status", response_model=ProcessingJobStatus)
def get_project_status(project_id: str, db: Session = Depends(get_db)):
    job = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found for this project.")
    return job

@router.get("/{project_id}/segments", response_model=List[ContentSegmentResponse])
def get_project_segments(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project.segments

@router.get("/{project_id}/requirements", response_model=List[AssetRequirementResponse])
def get_project_requirements(project_id: str, db: Session = Depends(get_db)):
    reqs = db.query(AssetRequirement).join(ContentSegment).filter(ContentSegment.project_id == project_id).all()
    return reqs

@router.get("/{project_id}/assets", response_model=List[AssetResponse])
def get_project_assets(project_id: str, db: Session = Depends(get_db)):
    assets = db.query(Asset).join(AssetRequirement).join(ContentSegment).filter(ContentSegment.project_id == project_id).all()
    return assets

@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
def get_project_summary(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    segments = project.segments
    total_scenes = len(segments)
    
    requirements = db.query(AssetRequirement).join(ContentSegment).filter(ContentSegment.project_id == project_id).all()
    total_requirements = len(requirements)

    assets = db.query(Asset).join(AssetRequirement).join(ContentSegment).filter(ContentSegment.project_id == project_id).all()
    total_assets = len(assets)

    high_confidence_matches = sum(1 for a in assets if a.relevance_score >= 80)
    manual_review_items = sum(1 for a in assets if a.status == "flagged" or "manual" in a.license_info.lower())
    
    unique_sources = len(set(a.source for a in assets))

    # Transparent calculation: Average 5 minutes per asset manually vs SLAYERS automated pipeline (~15 seconds)
    estimated_manual_time_minutes = total_requirements * 5
    
    slayers_time = 15
    if project.processing_job and project.processing_job.completed_at and project.processing_job.started_at:
        delta = (project.processing_job.completed_at - project.processing_job.started_at).total_seconds()
        slayers_time = max(5, int(delta))

    return ProjectSummaryResponse(
        project_id=project_id,
        total_scenes=total_scenes,
        total_requirements=total_requirements,
        total_assets=total_assets,
        high_confidence_matches=high_confidence_matches,
        total_sources=unique_sources,
        manual_review_items=manual_review_items,
        estimated_manual_time_minutes=estimated_manual_time_minutes,
        slayers_processing_time_seconds=slayers_time
    )

@router.post("/demo", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_demo_project(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Creates a sample demo project for instant hackathon demonstration."""
    demo_script = """
The software industry is undergoing a massive shift as AI coding agents emerge.
Developers no longer spend hours writing boilerplate code manually.
Instead, intelligent agents analyze repositories, create implementation plans, and write multi-file features.
For example, modern IDE interfaces now feature AI pair-programmers integrated right into the editor window.
This transformation allows small engineering teams to build complex software in a fraction of the time.
""".strip()

    project = Project(
        name="How AI Coding Agents are Changing Software Development (Demo Project)",
        source_type="script",
        source_text=demo_script,
        status="draft"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    job = ProcessingJob(
        project_id=project.id,
        status="pending",
        current_step="Created",
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(project)

    background_tasks.add_task(process_project_pipeline, project.id)

    return project
