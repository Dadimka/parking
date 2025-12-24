"""Database models package."""

from app.db.base import Base
from app.db.models.camera import Camera
from app.db.models.parking_lot import ParkingLot
from app.db.models.parking_slot import ParkingSlot
from app.db.models.video import Video
from app.db.models.occupancy_event import OccupancyEvent
from app.db.models.detection import Detection

__all__ = [
    "Base",
    "Camera",
    "ParkingLot",
    "ParkingSlot",
    "Video",
    "OccupancyEvent",
    "Detection",
]
