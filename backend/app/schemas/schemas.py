"""
Pydantic v2 schemas for all SLAYERS API request/response contracts.
All schemas use from_attributes=True for ORM interop.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Optional, Any, Dict
from datetime import datetime

# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------
class AssetResponse(BaseModel):
    id: str
    requirement_id: str
    title: str
    source: str
    source_url: str
    asset_url: str
    thumbnail_url: Optional[str] = None
    asset_type: str
    relevance_score: int = Field(ge=0, le=100)
    license_info: str
    license_url: Optional[str] = None
    usage_notes: Optional[str] = None
    usage_status: str = "verify_manually"
    status: str
    provider_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Asset Requirement
# ---------------------------------------------------------------------------
class AssetRequirementResponse(BaseModel):
    id: str
    segment_id: str
    asset_type: str
    description: str
    search_query: str
    priority: str
    reason: Optional[str] = None
    assets: List[AssetResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Content Segment
# ---------------------------------------------------------------------------
class ContentSegmentResponse(BaseModel):
    id: str
    project_id: str
    sequence: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    text: str
    scene_description: Optional[str] = None
    visual_intent: Optional[str] = None
    importance: str
    requirements: List[AssetRequirementResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Processing Job
# ---------------------------------------------------------------------------
class ProcessingJobStatus(BaseModel):
    id: str
    project_id: str
    status: str
    current_step: str
    progress: int
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    provider_stats: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
VALID_SOURCE_TYPES = {"script", "transcript", "text"}
VALID_STATUSES = {"draft", "processing", "completed", "failed"}

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: str = Field(default="script")
    source_text: str = Field(min_length=1)

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in VALID_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {sorted(VALID_SOURCE_TYPES)}")
        return v

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_text must not be empty or only whitespace.")
        if len(v) > 20000:
            raise ValueError("source_text exceeds maximum length of 20,000 characters.")
        return v


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
    high_confidence_matches: int
    needs_review: int
    total_sources: int
    provider_breakdown: Dict[str, int]
    actual_processing_seconds: int
    manual_estimate_minutes: int
