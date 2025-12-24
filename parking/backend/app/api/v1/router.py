"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import cameras, parking_lots, parking_slots, videos, events, detections

api_router = APIRouter()

api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(parking_lots.router, prefix="/parking-lots", tags=["parking-lots"])
api_router.include_router(parking_slots.router, prefix="/parking-slots", tags=["parking-slots"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(detections.router, tags=["detections"])
