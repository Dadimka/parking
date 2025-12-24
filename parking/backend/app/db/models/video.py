"""Video model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Video(Base):
    """Video file metadata and processing status."""

    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String(512), nullable=False)
    upload_time = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Optional: actual video start time (from metadata or user input)
    video_start_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)

    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_finished_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)

    # TaskIQ task ID for tracking
    task_id = Column(String(255), nullable=True)

    # Relationships
    camera = relationship("Camera", back_populates="videos")
    occupancy_events = relationship(
        "OccupancyEvent",
        back_populates="video",
        cascade="all, delete-orphan",
    )
    detections = relationship(
        "Detection",
        back_populates="video",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Video(id={self.id}, filename={self.filename}, processed={self.processed})>"
