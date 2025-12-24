"""Detection schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Bounding box schema."""

    x1: float
    y1: float
    x2: float
    y2: float


class DetectionBase(BaseModel):
    """Base detection schema."""

    video_id: UUID
    camera_id: UUID
    frame_number: int
    frame_time: datetime
    offset_seconds: float
    class_id: int
    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: dict
    bbox_normalized: dict
    track_id: Optional[int] = None


class DetectionCreate(DetectionBase):
    """Schema for creating a detection."""

    pass


class DetectionResponse(BaseModel):
    """Schema for detection response."""

    id: UUID
    video_id: UUID
    camera_id: UUID
    frame_number: int
    frame_time: datetime
    offset_seconds: float
    class_id: int
    class_name: str
    confidence: float
    bbox: dict
    bbox_normalized: dict
    track_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class DetectionWithSlot(DetectionResponse):
    """Detection with associated parking slot info."""

    parking_slot_id: Optional[UUID] = None
    parking_slot_name: Optional[str] = None
    iou: Optional[float] = None
    is_in_slot: bool = False


class FrameDetections(BaseModel):
    """All detections for a specific frame."""

    frame_number: int
    frame_time: datetime
    offset_seconds: float
    detections: list[DetectionWithSlot]
    total_vehicles: int
