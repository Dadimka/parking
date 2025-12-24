"""OccupancyEvent schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box schema."""

    x: float
    y: float
    w: float
    h: float


class OccupancyEventBase(BaseModel):
    """Base occupancy event schema."""

    video_id: UUID
    camera_id: UUID
    parking_lot_id: UUID
    parking_slot_id: Optional[UUID] = None
    frame_time: datetime
    offset_seconds: float
    status: str = Field(..., pattern="^(occupied|free|unknown)$")
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class OccupancyEventCreate(OccupancyEventBase):
    """Schema for creating an occupancy event."""

    pass


class OccupancyEventResponse(BaseModel):
    """Schema for occupancy event response."""

    id: UUID
    video_id: UUID
    camera_id: UUID
    parking_lot_id: UUID
    parking_slot_id: Optional[UUID]
    frame_time: datetime
    offset_seconds: float
    status: str
    bbox: Optional[dict]
    confidence: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class OccupancyStats(BaseModel):
    """Schema for occupancy statistics."""

    total_slots: int
    occupied_slots: int
    free_slots: int
    unknown_slots: int
    occupancy_rate: float
    timestamp: datetime
