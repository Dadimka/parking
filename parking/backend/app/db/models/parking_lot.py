"""ParkingLot model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ParkingLot(Base):
    """Parking lot - represents a parking area (polygon) within camera view."""

    __tablename__ = "parking_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    # GeoJSON-like polygon: {"type": "Polygon", "coordinates": [[[x,y], ...]]}
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
    camera = relationship("Camera", back_populates="parking_lots")
    occupancy_events = relationship(
        "OccupancyEvent",
        back_populates="parking_lot",
    )

    def __repr__(self):
        return f"<ParkingLot(id={self.id}, name={self.name})>"
