"""Detections API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models import Detection, ParkingSlot
from app.schemas.detection import (
    DetectionResponse,
    DetectionWithSlot,
    FrameDetections,
)
from shapely.geometry import Polygon, box

router = APIRouter()


def polygon_from_geojson(geojson_data: dict) -> Polygon:
    """Convert GeoJSON polygon to Shapely Polygon."""
    coordinates = geojson_data.get("coordinates", [[]])[0]
    return Polygon([(pt[0], pt[1]) for pt in coordinates])


def bbox_to_polygon(bbox_norm: dict) -> Polygon:
    """Convert normalized bbox to Shapely Polygon."""
    return box(bbox_norm["x1"], bbox_norm["y1"], bbox_norm["x2"], bbox_norm["y2"])


def calculate_iou(poly1: Polygon, poly2: Polygon) -> float:
    """Calculate Intersection over Union between two polygons."""
    try:
        intersection = poly1.intersection(poly2).area
        union = poly1.union(poly2).area
        return intersection / union if union > 0 else 0.0
    except Exception:
        return 0.0


@router.get("/detections/", response_model=List[DetectionResponse])
async def get_detections(
    video_id: Optional[UUID] = None,
    camera_id: Optional[UUID] = None,
    class_name: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get raw detections with optional filters."""
    query = select(Detection)

    if video_id:
        query = query.where(Detection.video_id == video_id)
    if camera_id:
        query = query.where(Detection.camera_id == camera_id)
    if class_name:
        query = query.where(Detection.class_name == class_name)
    if min_confidence is not None:
        query = query.where(Detection.confidence >= min_confidence)

    query = query.order_by(Detection.frame_time.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    detections = result.scalars().all()

    return detections


@router.get("/detections/video/{video_id}/frames", response_model=List[FrameDetections])
async def get_detections_by_frames(
    video_id: UUID,
    camera_id: UUID,
    iou_threshold: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detections grouped by frames with parking slot association.
    Uses IoU to determine which slot each detection belongs to.
    """
    # Get unique frame numbers for this video
    frames_query = (
        select(Detection.frame_number)
        .where(Detection.video_id == video_id)
        .distinct()
        .order_by(Detection.frame_number)
        .limit(limit)
        .offset(offset)
    )
    frames_result = await db.execute(frames_query)
    frame_numbers = [row[0] for row in frames_result.all()]

    if not frame_numbers:
        return []

    # Get all detections for these frames
    detections_query = (
        select(Detection)
        .where(Detection.video_id == video_id, Detection.frame_number.in_(frame_numbers))
        .order_by(Detection.frame_number, Detection.created_at)
    )
    detections_result = await db.execute(detections_query)
    detections = detections_result.scalars().all()

    # Get parking slots for this camera
    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    # Convert slots to Shapely polygons
    slot_polygons = {
        slot.id: (polygon_from_geojson(slot.polygon), slot.name) for slot in parking_slots
    }

    # Group detections by frame and associate with slots
    frames_data = {}
    for detection in detections:
        if detection.frame_number not in frames_data:
            frames_data[detection.frame_number] = {
                "frame_number": detection.frame_number,
                "frame_time": detection.frame_time,
                "offset_seconds": detection.offset_seconds,
                "detections": [],
                "total_vehicles": 0,
            }

        # Convert detection bbox to polygon
        detection_polygon = bbox_to_polygon(detection.bbox_normalized)

        # Find best matching slot
        best_slot_id = None
        best_slot_name = None
        best_iou = 0.0

        for slot_id, (slot_polygon, slot_name) in slot_polygons.items():
            iou = calculate_iou(detection_polygon, slot_polygon)
            if iou > best_iou and iou >= iou_threshold:
                best_iou = iou
                best_slot_id = slot_id
                best_slot_name = slot_name

        # Create detection with slot info
        detection_with_slot = DetectionWithSlot(
            id=detection.id,
            video_id=detection.video_id,
            camera_id=detection.camera_id,
            frame_number=detection.frame_number,
            frame_time=detection.frame_time,
            offset_seconds=detection.offset_seconds,
            class_id=detection.class_id,
            class_name=detection.class_name,
            confidence=detection.confidence,
            bbox=detection.bbox,
            bbox_normalized=detection.bbox_normalized,
            track_id=detection.track_id,
            created_at=detection.created_at,
            parking_slot_id=best_slot_id,
            parking_slot_name=best_slot_name,
            iou=best_iou if best_slot_id else None,
            is_in_slot=best_slot_id is not None,
        )

        frames_data[detection.frame_number]["detections"].append(detection_with_slot)
        frames_data[detection.frame_number]["total_vehicles"] += 1

    # Convert to list and return
    result = [FrameDetections(**frame_data) for frame_data in frames_data.values()]
    result.sort(key=lambda x: x.frame_number)

    return result


@router.get("/detections/stats/by-class")
async def get_detection_stats_by_class(
    video_id: Optional[UUID] = None,
    camera_id: Optional[UUID] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get detection statistics grouped by vehicle class."""
    query = select(
        Detection.class_name,
        func.count(Detection.id).label("count"),
        func.avg(Detection.confidence).label("avg_confidence"),
        func.min(Detection.confidence).label("min_confidence"),
        func.max(Detection.confidence).label("max_confidence"),
    ).group_by(Detection.class_name)

    if video_id:
        query = query.where(Detection.video_id == video_id)
    if camera_id:
        query = query.where(Detection.camera_id == camera_id)
    if start_time:
        query = query.where(Detection.frame_time >= start_time)
    if end_time:
        query = query.where(Detection.frame_time <= end_time)

    result = await db.execute(query)
    stats = result.all()

    return [
        {
            "class_name": row.class_name,
            "count": row.count,
            "avg_confidence": float(row.avg_confidence),
            "min_confidence": float(row.min_confidence),
            "max_confidence": float(row.max_confidence),
        }
        for row in stats
    ]


@router.get("/detections/video/{video_id}/frame/{frame_number}")
async def get_frame_detections(
    video_id: UUID,
    frame_number: int,
    camera_id: UUID,
    iou_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detections for a specific frame with slot association.
    Useful for timeline playback synchronization.
    """
    # Get detections for this frame
    detections_query = select(Detection).where(
        Detection.video_id == video_id, Detection.frame_number == frame_number
    )
    detections_result = await db.execute(detections_query)
    detections = detections_result.scalars().all()

    if not detections:
        return {
            "frame_number": frame_number,
            "frame_time": None,
            "offset_seconds": None,
            "total_vehicles": 0,
            "detections": [],
            "occupancy": {"occupied_slots": [], "total_detections": 0},
        }

    # Get parking slots for this camera
    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    # Convert slots to polygons
    slot_polygons = {
        slot.id: (polygon_from_geojson(slot.polygon), slot.name) for slot in parking_slots
    }

    # Process detections and find slot associations
    detections_with_slots = []
    occupied_slot_ids = set()

    for detection in detections:
        detection_polygon = bbox_to_polygon(detection.bbox_normalized)

        # Find best matching slot
        best_slot_id = None
        best_slot_name = None
        best_iou = 0.0

        for slot_id, (slot_polygon, slot_name) in slot_polygons.items():
            iou = calculate_iou(detection_polygon, slot_polygon)
            if iou > best_iou and iou >= iou_threshold:
                best_iou = iou
                best_slot_id = slot_id
                best_slot_name = slot_name

        if best_slot_id:
            occupied_slot_ids.add(best_slot_id)

        detections_with_slots.append(
            {
                "id": str(detection.id),
                "class_name": detection.class_name,
                "confidence": detection.confidence,
                "bbox": detection.bbox,
                "bbox_normalized": detection.bbox_normalized,
                "parking_slot_id": str(best_slot_id) if best_slot_id else None,
                "parking_slot_name": best_slot_name,
                "iou": best_iou if best_slot_id else None,
                "is_in_slot": best_slot_id is not None,
            }
        )

    first_detection = detections[0]

    return {
        "frame_number": frame_number,
        "frame_time": first_detection.frame_time.isoformat(),
        "offset_seconds": first_detection.offset_seconds,
        "total_vehicles": len(detections),
        "detections": detections_with_slots,
        "occupancy": {
            "occupied_slots": [str(slot_id) for slot_id in occupied_slot_ids],
            "occupied_count": len(occupied_slot_ids),
            "free_count": len(parking_slots) - len(occupied_slot_ids),
            "occupancy_rate": len(occupied_slot_ids) / len(parking_slots) if parking_slots else 0,
        },
    }


@router.get("/detections/stats/occupancy")
async def get_occupancy_stats(
    video_id: UUID,
    camera_id: UUID,
    iou_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get occupancy statistics by analyzing detections vs parking slots.
    Returns slot-level occupancy over time.
    """
    # Get all detections for this video
    detections_query = (
        select(Detection).where(Detection.video_id == video_id).order_by(Detection.frame_number)
    )
    detections_result = await db.execute(detections_query)
    detections = detections_result.scalars().all()

    # Get parking slots for this camera
    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    # Convert slots to Shapely polygons
    slot_polygons = {
        slot.id: (polygon_from_geojson(slot.polygon), slot.name) for slot in parking_slots
    }

    # Analyze occupancy per frame
    frame_occupancy = {}

    for detection in detections:
        frame_num = detection.frame_number

        if frame_num not in frame_occupancy:
            frame_occupancy[frame_num] = {
                "frame_number": frame_num,
                "frame_time": detection.frame_time,
                "occupied_slots": set(),
                "detections": 0,
            }

        # Convert detection bbox to polygon
        detection_polygon = bbox_to_polygon(detection.bbox_normalized)

        # Check which slot this detection belongs to
        for slot_id, (slot_polygon, slot_name) in slot_polygons.items():
            iou = calculate_iou(detection_polygon, slot_polygon)
            if iou >= iou_threshold:
                frame_occupancy[frame_num]["occupied_slots"].add(slot_id)

        frame_occupancy[frame_num]["detections"] += 1

    # Calculate statistics
    total_slots = len(parking_slots)
    occupancy_timeline = []

    for frame_data in sorted(frame_occupancy.values(), key=lambda x: x["frame_number"]):
        occupied_count = len(frame_data["occupied_slots"])
        occupancy_timeline.append(
            {
                "frame_number": frame_data["frame_number"],
                "frame_time": frame_data["frame_time"],
                "total_slots": total_slots,
                "occupied_slots": occupied_count,
                "free_slots": total_slots - occupied_count,
                "occupancy_rate": occupied_count / total_slots if total_slots > 0 else 0,
                "total_detections": frame_data["detections"],
            }
        )

    # Calculate overall statistics
    avg_occupancy = (
        sum(d["occupancy_rate"] for d in occupancy_timeline) / len(occupancy_timeline)
        if occupancy_timeline
        else 0
    )

    return {
        "video_id": str(video_id),
        "camera_id": str(camera_id),
        "total_slots": total_slots,
        "frames_analyzed": len(occupancy_timeline),
        "average_occupancy_rate": avg_occupancy,
        "timeline": occupancy_timeline,
    }
