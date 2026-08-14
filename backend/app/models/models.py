"""
SQLAlchemy ORM models for SLAYERS.

Hierarchy:
  Project → ContentSegment → AssetRequirement → Asset
  Project → ProcessingJob (1:1)

All IDs are UUIDs (string). Cascades ensure referential integrity on delete.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime,
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False, default="script")
    source_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    segments = relationship(
        "ContentSegment",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ContentSegment.sequence",
        lazy="select"
    )
    processing_job = relationship(
        "ProcessingJob",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_projects_status", "status"),
        Index("ix_projects_created_at", "created_at"),
    )


class ContentSegment(Base):
    __tablename__ = "content_segments"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    start_time = Column(String(20), nullable=True)
    end_time = Column(String(20), nullable=True)
    text = Column(Text, nullable=False)
    scene_description = Column(Text, nullable=True)
    visual_intent = Column(String(100), nullable=True)
    importance = Column(String(20), nullable=False, default="medium")

    project = relationship("Project", back_populates="segments")
    requirements = relationship(
        "AssetRequirement",
        back_populates="segment",
        cascade="all, delete-orphan",
        lazy="select"
    )

    __table_args__ = (
        Index("ix_segments_project_id", "project_id"),
        Index("ix_segments_sequence", "project_id", "sequence"),
    )


class AssetRequirement(Base):
    __tablename__ = "asset_requirements"

    id = Column(String(36), primary_key=True, default=_uuid)
    segment_id = Column(String(36), ForeignKey("content_segments.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    search_query = Column(String(500), nullable=False)
    priority = Column(String(20), nullable=False, default="medium")
    reason = Column(Text, nullable=True)

    segment = relationship("ContentSegment", back_populates="requirements")
    assets = relationship(
        "Asset",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="Asset.relevance_score.desc()",
        lazy="select"
    )

    __table_args__ = (
        Index("ix_requirements_segment_id", "segment_id"),
    )


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=_uuid)
    requirement_id = Column(String(36), ForeignKey("asset_requirements.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=False)
    source_url = Column(Text, nullable=False)
    asset_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    asset_type = Column(String(50), nullable=False)
    relevance_score = Column(Integer, nullable=False, default=50)
    license_info = Column(String(500), nullable=False, default="VERIFY_MANUALLY")
    license_url = Column(Text, nullable=True)
    usage_notes = Column(Text, nullable=True)
    usage_status = Column(String(50), nullable=False, default="verify_manually")
    status = Column(String(50), nullable=False, default="alternative")
    provider_id = Column(String(255), nullable=True)   # provider's own asset id for deduplication
    metadata_json = Column(JSON, nullable=True)

    requirement = relationship("AssetRequirement", back_populates="assets")

    __table_args__ = (
        Index("ix_assets_requirement_id", "requirement_id"),
        Index("ix_assets_relevance_score", "relevance_score"),
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String(50), nullable=False, default="pending")
    current_step = Column(String(255), nullable=False, default="Initialized")
    progress = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    warnings = Column(JSON, nullable=True)           # list[str] provider warnings
    provider_stats = Column(JSON, nullable=True)     # dict: provider → {found, failed}
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="processing_job")

    __table_args__ = (
        Index("ix_jobs_project_id", "project_id"),
        Index("ix_jobs_status", "status"),
    )
