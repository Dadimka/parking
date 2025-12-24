"""Detection model - raw YOLO detections."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Detection(Base):
    """Raw vehicle detection from YOLO model."""

    __tablename__ = "detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Time information
    frame_number = Column(Integer, nullable=False)
    frame_time = Column(DateTime(timezone=True), nullable=False)
    offset_seconds = Column(Float, nullable=False)

    # Detection information
    class_id = Column(Integer, nullable=False)  # YOLO class ID
    class_name = Column(String(64), nullable=False)  # car, motorcycle, bus, truck
    confidence = Column(Float, nullable=False)

    # Bounding box in absolute coordinates (pixels)
    bbox = Column(JSONB, nullable=False)  # {"x1": float, "y1": float, "x2": float, "y2": float}

    # Normalized bounding box (0-1 range) for easier comparison with polygons
    bbox_normalized = Column(
        JSONB, nullable=False
    )  # {"x1": float, "y1": float, "x2": float, "y2": float}

    # Optional: track_id if using YOLO tracking
    track_id = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    video = relationship("Video", back_populates="detections")
    camera = relationship("Camera", back_populates="detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, class={self.class_name}, conf={self.confidence:.2f})>"
