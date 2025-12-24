"""Video schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VideoBase(BaseModel):
    """Base video schema."""

    camera_id: UUID
    video_start_time: Optional[datetime] = None


class VideoCreate(VideoBase):
    """Schema for creating a video."""

    pass


class VideoUpdate(BaseModel):
    """Schema for updating a video."""

    video_start_time: Optional[datetime] = None


class VideoResponse(BaseModel):
    """Schema for video response."""

    id: UUID
    camera_id: UUID
    filename: str
    upload_time: datetime
    video_start_time: Optional[datetime]
    duration_seconds: Optional[float]
    fps: Optional[float]
    processed: bool
    processing_started_at: Optional[datetime]
    processing_finished_at: Optional[datetime]
    processing_error: Optional[str]
    task_id: Optional[str]

    model_config = {"from_attributes": True}


class VideoUploadResponse(BaseModel):
    """Schema for video upload response."""

    video_id: UUID
    filename: str
    task_id: Optional[str]
    message: str


class VideoProcessingStatus(BaseModel):
    """Schema for video processing status."""

    video_id: UUID
    processed: bool
    processing_started_at: Optional[datetime]
    processing_finished_at: Optional[datetime]
    processing_error: Optional[str]
    task_id: Optional[str]
    progress_percentage: Optional[float] = None
