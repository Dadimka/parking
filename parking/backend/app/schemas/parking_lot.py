"""ParkingLot schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PolygonCoordinates(BaseModel):
    """GeoJSON polygon coordinates."""

    type: str = Field(default="Polygon")
    coordinates: List[List[List[float]]]


class ParkingLotBase(BaseModel):
    """Base parking lot schema."""

    camera_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    polygon: PolygonCoordinates


class ParkingLotCreate(ParkingLotBase):
    """Schema for creating a parking lot."""

    pass


class ParkingLotUpdate(BaseModel):
    """Schema for updating a parking lot."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    polygon: Optional[PolygonCoordinates] = None


class ParkingLotResponse(BaseModel):
    """Schema for parking lot response."""

    id: UUID
    camera_id: UUID
    name: str
    polygon: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
