"""OccupancyEvent model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class OccupancyEvent(Base):
    """Occupancy detection event - records parking space status at a point in time."""

    __tablename__ = "occupancy_events"

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
    parking_lot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_lots.id", ondelete="CASCADE"),
        nullable=False,
    )
    parking_slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_slots.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Time information
    frame_time = Column(DateTime(timezone=True), nullable=False)
    offset_seconds = Column(Float, nullable=False)

    # Detection information
    status = Column(String(16), nullable=False)  # 'occupied', 'free', 'unknown'
    # Bounding box: {"x": float, "y": float, "w": float, "h": float}
    bbox = Column(JSONB, nullable=True)
    confidence = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('occupied', 'free', 'unknown')", name="check_status"),
    )

    # Relationships
    video = relationship("Video", back_populates="occupancy_events")
    camera = relationship("Camera", back_populates="occupancy_events")
    parking_lot = relationship("ParkingLot", back_populates="occupancy_events")
    parking_slot = relationship("ParkingSlot", back_populates="occupancy_events")

    def __repr__(self):
        return f"<OccupancyEvent(id={self.id}, status={self.status}, frame_time={self.frame_time})>"
