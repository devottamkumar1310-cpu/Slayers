from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- Asset Schemas ---
class AssetBase(BaseModel):
    title: str
    source: str
    source_url: str
    asset_url: str
    thumbnail_url: Optional[str] = None
    asset_type: str
    relevance_score: int = Field(ge=0, le=100)
    license_info: str = "Verify manually"
    usage_notes: Optional[str] = None
    status: str = "recommended"
    metadata_json: Optional[Dict[str, Any]] = None

class AssetCreate(AssetBase):
    requirement_id: str

class AssetResponse(AssetBase):
    id: str
    requirement_id: str

    model_config = ConfigDict(from_attributes=True)


# --- Asset Requirement Schemas ---
class AssetRequirementBase(BaseModel):
    asset_type: str
    description: str
    search_query: str
    priority: str = "medium"
    reason: Optional[str] = None

class AssetRequirementCreate(AssetRequirementBase):
    segment_id: str

class AssetRequirementResponse(AssetRequirementBase):
    id: str
    segment_id: str
    assets: List[AssetResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Content Segment Schemas ---
class ContentSegmentBase(BaseModel):
    sequence: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    text: str
    scene_description: Optional[str] = None
    visual_intent: Optional[str] = None
    importance: str = "medium"

class ContentSegmentCreate(ContentSegmentBase):
    project_id: str

class ContentSegmentResponse(ContentSegmentBase):
    id: str
    project_id: str
    requirements: List[AssetRequirementResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Processing Job Schemas ---
class ProcessingJobStatus(BaseModel):
    id: str
    project_id: str
    status: str
    current_step: str
    progress: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str
    source_type: str = "script" # script, transcript, text
    source_text: str

class ProjectResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source_text: str
    status: str
    created_at: datetime
    updated_at: datetime
    segments: List[ContentSegmentResponse] = []
    processing_job: Optional[ProcessingJobStatus] = None

    model_config = ConfigDict(from_attributes=True)

class ProjectSummaryResponse(BaseModel):
    project_id: str
    total_scenes: int
    total_requirements: int
    total_assets: int
    high_confidence_matches: int # relevance_score >= 80
    total_sources: int
    manual_review_items: int
    estimated_manual_time_minutes: int
    slayers_processing_time_seconds: int

