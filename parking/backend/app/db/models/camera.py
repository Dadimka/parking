"""Camera model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Camera(Base):
    """Camera model - represents a physical camera."""

    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    preview_image = Column(String(512), nullable=True)  # Path to preview image
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    parking_lots = relationship(
        "ParkingLot",
        back_populates="camera",
        cascade="all, delete-orphan",
    )
    parking_slots = relationship(
        "ParkingSlot",
        back_populates="camera",
        cascade="all, delete-orphan",
    )
    videos = relationship(
        "Video",
        back_populates="camera",
        cascade="all, delete-orphan",
    )
    occupancy_events = relationship(
        "OccupancyEvent",
        back_populates="camera",
    )
    detections = relationship(
        "Detection",
        back_populates="camera",
    )

    def __repr__(self):
        return f"<Camera(id={self.id}, name={self.name})>"
