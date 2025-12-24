"""Schemas package."""

from app.schemas.camera import CameraCreate, CameraResponse
from app.schemas.occupancy_event import OccupancyEventCreate, OccupancyEventResponse
from app.schemas.parking_lot import ParkingLotCreate, ParkingLotResponse
from app.schemas.parking_slot import ParkingSlotCreate, ParkingSlotResponse
from app.schemas.video import VideoCreate, VideoResponse
from app.schemas.detection import (
    DetectionCreate,
    DetectionResponse,
    DetectionWithSlot,
    FrameDetections,
)

__all__ = [
    "CameraCreate",
    "CameraResponse",
    "OccupancyEventCreate",
    "OccupancyEventResponse",
    "ParkingLotCreate",
    "ParkingLotResponse",
    "ParkingSlotCreate",
    "ParkingSlotResponse",
    "VideoCreate",
    "VideoResponse",
    "DetectionCreate",
    "DetectionResponse",
    "DetectionWithSlot",
    "FrameDetections",
]
