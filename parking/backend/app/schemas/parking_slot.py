"""ParkingSlot schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.parking_lot import PolygonCoordinates


class ParkingSlotBase(BaseModel):
    """Base parking slot schema."""

    camera_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    polygon: PolygonCoordinates


class ParkingSlotCreate(ParkingSlotBase):
    """Schema for creating a parking slot."""

    pass


class ParkingSlotUpdate(BaseModel):
    """Schema for updating a parking slot."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    polygon: Optional[PolygonCoordinates] = None


class ParkingSlotResponse(BaseModel):
    """Schema for parking slot response."""

    id: UUID
    camera_id: UUID
    name: str
    polygon: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParkingSlotWithStatus(ParkingSlotResponse):
    """Schema for parking slot with current status."""

    current_status: str = "unknown"  # 'occupied', 'free', 'unknown'
    last_updated: Optional[datetime] = None
