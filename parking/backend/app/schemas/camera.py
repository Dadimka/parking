"""Camera schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CameraBase(BaseModel):
    """Base camera schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    preview_image: Optional[str] = None


class CameraCreate(CameraBase):
    """Schema for creating a camera."""

    pass


class CameraUpdate(BaseModel):
    """Schema for updating a camera."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    preview_image: Optional[str] = None


class CameraResponse(CameraBase):
    """Schema for camera response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CameraWithStats(CameraResponse):
    """Schema for camera with statistics."""

    total_videos: int = 0
    total_parking_lots: int = 0
    total_parking_slots: int = 0
