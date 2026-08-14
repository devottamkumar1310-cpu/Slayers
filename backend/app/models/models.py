import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False, default="script")  # script, transcript, text
    source_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="draft")  # draft, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    segments = relationship("ContentSegment", back_populates="project", cascade="all, delete-orphan", order_by="ContentSegment.sequence")
    processing_job = relationship("ProcessingJob", back_populates="project", uselist=False, cascade="all, delete-orphan")


class ContentSegment(Base):
    __tablename__ = "content_segments"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    sequence = Column(Integer, nullable=False, default=1)
    start_time = Column(String(50), nullable=True)  # e.g., "00:00"
    end_time = Column(String(50), nullable=True)    # e.g., "00:08"
    text = Column(Text, nullable=False)
    scene_description = Column(Text, nullable=True)
    visual_intent = Column(String(100), nullable=True) # e.g. product_ui, stock_footage, diagram
    importance = Column(String(50), nullable=False, default="medium") # high, medium, low

    project = relationship("Project", back_populates="segments")
    requirements = relationship("AssetRequirement", back_populates="segment", cascade="all, delete-orphan")


class AssetRequirement(Base):
    __tablename__ = "asset_requirements"

    id = Column(String, primary_key=True, default=generate_uuid)
    segment_id = Column(String, ForeignKey("content_segments.id"), nullable=False)
    asset_type = Column(String(100), nullable=False) # e.g. product_ui, stock_footage, logo, etc.
    description = Column(Text, nullable=False)
    search_query = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False, default="medium") # high, medium, low
    reason = Column(Text, nullable=True)

    segment = relationship("ContentSegment", back_populates="requirements")
    assets = relationship("Asset", back_populates="requirement", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=generate_uuid)
    requirement_id = Column(String, ForeignKey("asset_requirements.id"), nullable=False)
    title = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False) # e.g. Wikimedia Commons, Pexels, Unsplash
    source_url = Column(Text, nullable=False)
    asset_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    asset_type = Column(String(50), nullable=False) # image, video, logo, screenshot
    relevance_score = Column(Integer, nullable=False, default=50) # 0 to 100
    license_info = Column(String(255), nullable=False, default="Verify manually")
    usage_notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="recommended") # recommended, alternative, flagged
    metadata_json = Column(JSON, nullable=True)

    requirement = relationship("AssetRequirement", back_populates="assets")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending") # pending, processing, completed, failed
    current_step = Column(String(255), nullable=False, default="Initialized")
    progress = Column(Integer, nullable=False, default=0) # 0 to 100
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="processing_job")
