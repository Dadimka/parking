"""ParkingSlot model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ParkingSlot(Base):
    """Individual parking slot within a lot."""

    __tablename__ = "parking_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    # GeoJSON-like polygon for individual slot
    polygon = Column(JSONB, nullable=False)
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
    camera = relationship("Camera", back_populates="parking_slots")
    occupancy_events = relationship(
        "OccupancyEvent",
        back_populates="parking_slot",
    )

    def __repr__(self):
        return f"<ParkingSlot(id={self.id}, name={self.name})>"
