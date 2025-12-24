"""Video endpoints."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.config import settings
from app.db.models import Camera, Video, Detection, ParkingSlot, ParkingLot
from app.schemas.video import VideoProcessingStatus, VideoResponse, VideoUploadResponse
from shapely.geometry import Polygon, box

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    camera_id: UUID = Form(...),
    video_start_time: Optional[datetime] = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload a video file for processing."""
    # Verify camera exists
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a video",
        )

    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    original_name = Path(file.filename or "video").stem
    extension = Path(file.filename or ".mp4").suffix
    filename = f"{camera_id}_{timestamp}_{original_name}{extension}"

    # Save file
    file_path = settings.VIDEO_STORAGE_PATH / filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create video record
    video = Video(
        camera_id=camera_id,
        filename=filename,
        video_start_time=video_start_time,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Trigger TaskIQ video processing task
    from app.tasks.video_tasks import process_video_task

    task = await process_video_task.kiq(str(video.id))
    video.task_id = task.task_id
    await db.commit()

    return VideoUploadResponse(
        video_id=video.id,
        filename=filename,
        task_id=video.task_id,
        message="Video uploaded successfully. Processing will start shortly.",
    )


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    camera_id: Optional[UUID] = Query(None, description="Filter by camera ID"),
    processed: Optional[bool] = Query(None, description="Filter by processing status"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    """List all videos."""
    query = select(Video).offset(skip).limit(limit).order_by(Video.upload_time.desc())

    if camera_id:
        query = query.where(Video.camera_id == camera_id)
    if processed is not None:
        query = query.where(Video.processed == processed)

    result = await db.execute(query)
    videos = result.scalars().all()
    return videos


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific video by ID."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found",
        )

    return video


@router.get("/{video_id}/status", response_model=VideoProcessingStatus)
async def get_video_processing_status(
    video_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get video processing status."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found",
        )

    # Calculate progress if processing
    progress = None
    if video.processing_started_at and not video.processed:
        # TODO: Get actual progress from TaskIQ task
        progress = 50.0  # Placeholder
    elif video.processed:
        progress = 100.0

    return VideoProcessingStatus(
        video_id=video.id,
        processed=video.processed,
        processing_started_at=video.processing_started_at,
        processing_finished_at=video.processing_finished_at,
        processing_error=video.processing_error,
        task_id=video.task_id,
        progress_percentage=progress,
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a video and its file."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found",
        )

    # Delete file if exists
    file_path = settings.VIDEO_STORAGE_PATH / video.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(video)
    await db.commit()


def polygon_from_geojson(geojson_data: dict) -> Polygon:
    """Convert GeoJSON polygon to Shapely Polygon."""
    coordinates = geojson_data.get("coordinates", [[]])[0]
    return Polygon([(pt[0], pt[1]) for pt in coordinates])


def bbox_to_polygon(bbox_norm: dict) -> Polygon:
    """Convert normalized bbox to Shapely Polygon."""
    return box(bbox_norm["x1"], bbox_norm["y1"], bbox_norm["x2"], bbox_norm["y2"])


def calculate_iou(poly1: Polygon, poly2: Polygon) -> float:
    """Calculate Intersection over Union."""
    try:
        intersection = poly1.intersection(poly2).area
        union = poly1.union(poly2).area
        return intersection / union if union > 0 else 0.0
    except Exception:
        return 0.0


def check_containment(slot_poly: Polygon, lot_poly: Polygon, threshold: float = 0.5) -> bool:
    """
    Check if slot is contained in lot.
    Returns True if at least threshold% of slot area is inside lot.
    Better than IoU when lot is much larger than slot.
    """
    try:
        intersection = slot_poly.intersection(lot_poly).area
        slot_area = slot_poly.area
        if slot_area == 0:
            return False
        coverage = intersection / slot_area
        return coverage >= threshold
    except Exception:
        return False


@router.get("/camera/{camera_id}/debug-slot-lot-mapping")
async def debug_slot_lot_mapping(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Debug endpoint to check slot-to-lot mapping with IoU values.
    """
    # Get parking lots
    lots_query = select(ParkingLot).where(ParkingLot.camera_id == camera_id)
    lots_result = await db.execute(lots_query)
    parking_lots = lots_result.scalars().all()

    # Get parking slots
    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    if not parking_lots:
        return {"error": "No parking lots found for this camera"}

    if not parking_slots:
        return {"error": "No parking slots found for this camera"}

    # Build lot polygons
    lot_polygons = {lot.id: (polygon_from_geojson(lot.polygon), lot.name) for lot in parking_lots}

    # Check each slot
    results = []
    for slot in parking_slots:
        slot_poly = polygon_from_geojson(slot.polygon)
        slot_info = {
            "slot_id": str(slot.id),
            "slot_name": slot.name,
            "slot_polygon": slot.polygon,
            "lot_matches": [],
        }

        for lot_id, (lot_poly, lot_name) in lot_polygons.items():
            iou = calculate_iou(slot_poly, lot_poly)

            # Calculate coverage (what % of slot is inside lot)
            intersection = slot_poly.intersection(lot_poly).area
            coverage = intersection / slot_poly.area if slot_poly.area > 0 else 0

            slot_info["lot_matches"].append(
                {
                    "lot_id": str(lot_id),
                    "lot_name": lot_name,
                    "iou": round(iou, 4),
                    "coverage": round(coverage, 4),
                    "meets_threshold": coverage >= 0.5,
                }
            )

        # Sort by IoU descending
        slot_info["lot_matches"].sort(key=lambda x: x["iou"], reverse=True)
        results.append(slot_info)

    return {
        "camera_id": str(camera_id),
        "total_lots": len(parking_lots),
        "total_slots": len(parking_slots),
        "lots": [
            {"id": str(lot.id), "name": lot.name, "polygon": lot.polygon} for lot in parking_lots
        ],
        "slot_mapping": results,
    }


@router.get("/camera/{camera_id}/current-status")
async def get_current_parking_status(
    camera_id: UUID,
    iou_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current parking status for a camera based on its latest processed video.
    Returns real-time occupancy information for dashboard display.
    """
    # Get latest processed video for camera
    video_query = (
        select(Video)
        .where(Video.camera_id == camera_id, Video.processed == True)
        .order_by(Video.processing_finished_at.desc())
        .limit(1)
    )
    video_result = await db.execute(video_query)
    video = video_result.scalar_one_or_none()

    if not video:
        return {
            "camera_id": str(camera_id),
            "status": "no_data",
            "message": "No processed videos found for this camera",
            "slots": [],
            "summary": {"total_slots": 0, "occupied": 0, "free": 0, "occupancy_rate": 0},
        }

    # Get parking slots
    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    if not parking_slots:
        return {
            "camera_id": str(camera_id),
            "status": "no_slots",
            "message": "No parking slots defined for this camera",
            "video_id": str(video.id),
            "slots": [],
            "summary": {"total_slots": 0, "occupied": 0, "free": 0, "occupancy_rate": 0},
        }

    # Get latest frame detections
    latest_frame_query = select(func.max(Detection.frame_number)).where(
        Detection.video_id == video.id
    )
    latest_frame_result = await db.execute(latest_frame_query)
    latest_frame = latest_frame_result.scalar()

    if latest_frame is None:
        return {
            "camera_id": str(camera_id),
            "status": "no_detections",
            "message": "No detections found in video",
            "video_id": str(video.id),
            "slots": [
                {"id": str(slot.id), "name": slot.name, "status": "unknown"}
                for slot in parking_slots
            ],
            "summary": {
                "total_slots": len(parking_slots),
                "occupied": 0,
                "free": len(parking_slots),
                "occupancy_rate": 0,
            },
        }

    # Get detections from latest frame
    detections_query = select(Detection).where(
        Detection.video_id == video.id, Detection.frame_number == latest_frame
    )
    detections_result = await db.execute(detections_query)
    detections = detections_result.scalars().all()

    # Convert slots to polygons
    slot_polygons = {
        slot.id: (polygon_from_geojson(slot.polygon), slot.name) for slot in parking_slots
    }

    # Check occupancy
    occupied_slots = set()

    for detection in detections:
        detection_polygon = bbox_to_polygon(detection.bbox_normalized)

        for slot_id, (slot_polygon, slot_name) in slot_polygons.items():
            iou = calculate_iou(detection_polygon, slot_polygon)
            if iou >= iou_threshold:
                occupied_slots.add(slot_id)

    # Build response
    slots_status = []
    for slot in parking_slots:
        is_occupied = slot.id in occupied_slots
        slots_status.append(
            {
                "id": str(slot.id),
                "name": slot.name,
                "status": "occupied" if is_occupied else "free",
                "polygon": slot.polygon,
            }
        )

    occupied_count = len(occupied_slots)
    total_slots = len(parking_slots)

    return {
        "camera_id": str(camera_id),
        "video_id": str(video.id),
        "status": "ok",
        "last_updated": (
            video.processing_finished_at.isoformat() if video.processing_finished_at else None
        ),
        "frame_number": latest_frame,
        "slots": slots_status,
        "summary": {
            "total_slots": total_slots,
            "occupied": occupied_count,
            "free": total_slots - occupied_count,
            "occupancy_rate": round(occupied_count / total_slots, 2) if total_slots > 0 else 0,
        },
    }


@router.get("/camera/{camera_id}/lots-status")
async def get_lots_parking_status(
    camera_id: UUID,
    iou_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current parking status aggregated by lots (zones).
    Returns simplified view with lot-level occupancy.
    """
    # Get latest processed video for camera
    video_query = (
        select(Video)
        .where(Video.camera_id == camera_id, Video.processed == True)
        .order_by(Video.processing_finished_at.desc())
        .limit(1)
    )
    video_result = await db.execute(video_query)
    video = video_result.scalar_one_or_none()

    if not video:
        return {
            "camera_id": str(camera_id),
            "status": "no_data",
            "message": "No processed videos found for this camera",
            "lots": [],
            "summary": {
                "total_lots": 0,
                "total_capacity": 0,
                "total_occupied": 0,
                "avg_occupancy_rate": 0,
            },
        }

    # Get parking lots and slots
    lots_query = select(ParkingLot).where(ParkingLot.camera_id == camera_id)
    lots_result = await db.execute(lots_query)
    parking_lots = lots_result.scalars().all()

    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    if not parking_lots:
        return {
            "camera_id": str(camera_id),
            "status": "no_lots",
            "message": "No parking lots defined for this camera",
            "video_id": str(video.id),
            "lots": [],
            "summary": {
                "total_lots": 0,
                "total_capacity": 0,
                "total_occupied": 0,
                "avg_occupancy_rate": 0,
            },
        }

    # Get latest frame detections
    latest_frame_query = select(func.max(Detection.frame_number)).where(
        Detection.video_id == video.id
    )
    latest_frame_result = await db.execute(latest_frame_query)
    latest_frame = latest_frame_result.scalar()

    if latest_frame is None:
        lot_status = [
            {"id": str(lot.id), "name": lot.name, "capacity": 0, "occupied": 0, "occupancy_rate": 0}
            for lot in parking_lots
        ]
        return {
            "camera_id": str(camera_id),
            "status": "no_detections",
            "video_id": str(video.id),
            "lots": lot_status,
            "summary": {
                "total_lots": len(parking_lots),
                "total_capacity": 0,
                "total_occupied": 0,
                "avg_occupancy_rate": 0,
            },
        }

    # Get detections from latest frame
    detections_query = select(Detection).where(
        Detection.video_id == video.id, Detection.frame_number == latest_frame
    )
    detections_result = await db.execute(detections_query)
    detections = detections_result.scalars().all()

    # Build lot and slot polygons
    lot_polygons = {lot.id: (polygon_from_geojson(lot.polygon), lot.name) for lot in parking_lots}
    slot_polygons = {
        slot.id: (polygon_from_geojson(slot.polygon), slot.name) for slot in parking_slots
    }

    # Map slots to lots using containment check
    slot_to_lot_map = {}
    for slot in parking_slots:
        slot_poly = polygon_from_geojson(slot.polygon)

        # Check which lot contains this slot (at least 50% overlap)
        for lot_id, (lot_poly, lot_name) in lot_polygons.items():
            if check_containment(slot_poly, lot_poly, threshold=0.5):
                slot_to_lot_map[slot.id] = lot_id
                break  # Assign to first matching lot

    # Check occupancy per slot
    occupied_slots = set()

    for detection in detections:
        detection_polygon = bbox_to_polygon(detection.bbox_normalized)

        for slot_id, (slot_polygon, slot_name) in slot_polygons.items():
            iou = calculate_iou(detection_polygon, slot_polygon)
            if iou >= iou_threshold:
                occupied_slots.add(slot_id)

    # Aggregate by lots
    lot_data = {lot.id: {"name": lot.name, "capacity": 0, "occupied": 0} for lot in parking_lots}

    for slot in parking_slots:
        lot_id = slot_to_lot_map.get(slot.id)
        if lot_id and lot_id in lot_data:
            lot_data[lot_id]["capacity"] += 1
            if slot.id in occupied_slots:
                lot_data[lot_id]["occupied"] += 1

    # Build response
    lots_status = []
    total_capacity = 0
    total_occupied = 0

    for lot_id, data in lot_data.items():
        capacity = data["capacity"]
        occupied = data["occupied"]
        occupancy_rate = occupied / capacity if capacity > 0 else 0

        lots_status.append(
            {
                "id": str(lot_id),
                "name": data["name"],
                "capacity": capacity,
                "occupied": occupied,
                "free": capacity - occupied,
                "occupancy_rate": round(occupancy_rate, 2),
                "status": (
                    "full"
                    if occupancy_rate >= 0.95
                    else (
                        "busy"
                        if occupancy_rate >= 0.7
                        else ("moderate" if occupancy_rate >= 0.3 else "free")
                    )
                ),
            }
        )

        total_capacity += capacity
        total_occupied += occupied

    lots_status.sort(key=lambda x: x["occupancy_rate"], reverse=True)

    avg_occupancy = total_occupied / total_capacity if total_capacity > 0 else 0

    return {
        "camera_id": str(camera_id),
        "video_id": str(video.id),
        "status": "ok",
        "last_updated": (
            video.processing_finished_at.isoformat() if video.processing_finished_at else None
        ),
        "frame_number": latest_frame,
        "lots": lots_status,
        "summary": {
            "total_lots": len(parking_lots),
            "total_capacity": total_capacity,
            "total_occupied": total_occupied,
            "total_free": total_capacity - total_occupied,
            "avg_occupancy_rate": round(avg_occupancy, 2),
        },
    }


@router.get("/{video_id}/analytics")
async def get_video_analytics(
    video_id: UUID,
    iou_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get comprehensive analytics for a processed video.
    Provides aggregated metrics for parking monitoring dashboard.
    """
    # Get video
    video_result = await db.execute(select(Video).where(Video.id == video_id))
    video = video_result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {video_id} not found"
        )

    # Get detections count
    detections_count_query = select(func.count(Detection.id)).where(Detection.video_id == video_id)
    detections_count_result = await db.execute(detections_count_query)
    total_detections = detections_count_result.scalar() or 0

    if total_detections == 0:
        return {
            "video_id": str(video_id),
            "video_filename": video.filename,
            "processed": video.processed,
            "duration_seconds": video.duration_seconds,
            "fps": video.fps,
            "total_detections": 0,
            "summary": {
                "total_vehicles": 0,
                "average_occupancy_rate": 0,
                "peak_occupancy": 0,
                "total_parking_slots": 0,
            },
            "vehicle_breakdown": [],
            "occupancy_timeline": [],
            "slot_statistics": [],
        }

    # Get all detections
    detections_query = (
        select(Detection).where(Detection.video_id == video_id).order_by(Detection.frame_number)
    )
    detections_result = await db.execute(detections_query)
    detections = detections_result.scalars().all()

    # Get parking slots
    slots_query = select(ParkingSlot).where(ParkingSlot.camera_id == video.camera_id)
    slots_result = await db.execute(slots_query)
    parking_slots = slots_result.scalars().all()

    # Convert slots to polygons
    slot_polygons = {
        slot.id: (polygon_from_geojson(slot.polygon), slot.name) for slot in parking_slots
    }

    # Aggregate by vehicle class
    vehicle_counts = {}
    for detection in detections:
        class_name = detection.class_name
        if class_name not in vehicle_counts:
            vehicle_counts[class_name] = {"count": 0, "total_confidence": 0}
        vehicle_counts[class_name]["count"] += 1
        vehicle_counts[class_name]["total_confidence"] += detection.confidence

    vehicle_breakdown = [
        {
            "class_name": class_name,
            "count": data["count"],
            "percentage": round(data["count"] / total_detections * 100, 1),
            "avg_confidence": round(data["total_confidence"] / data["count"], 2),
        }
        for class_name, data in sorted(
            vehicle_counts.items(), key=lambda x: x[1]["count"], reverse=True
        )
    ]

    # Analyze occupancy per frame
    frame_data = {}
    unique_frames = set()

    for detection in detections:
        frame_num = detection.frame_number
        unique_frames.add(frame_num)

        if frame_num not in frame_data:
            frame_data[frame_num] = {
                "frame_number": frame_num,
                "frame_time": detection.frame_time.isoformat(),
                "offset_seconds": detection.offset_seconds,
                "occupied_slots": set(),
                "total_vehicles": 0,
            }

        # Check which slot this detection belongs to
        detection_polygon = bbox_to_polygon(detection.bbox_normalized)

        for slot_id, (slot_polygon, slot_name) in slot_polygons.items():
            iou = calculate_iou(detection_polygon, slot_polygon)
            if iou >= iou_threshold:
                frame_data[frame_num]["occupied_slots"].add(slot_id)

        frame_data[frame_num]["total_vehicles"] += 1

    # Build timeline
    total_slots = len(parking_slots)
    occupancy_timeline = []
    occupancy_rates = []

    for frame_num in sorted(frame_data.keys()):
        data = frame_data[frame_num]
        occupied = len(data["occupied_slots"])
        free = total_slots - occupied
        occupancy_rate = occupied / total_slots if total_slots > 0 else 0
        occupancy_rates.append(occupancy_rate)

        occupancy_timeline.append(
            {
                "frame_number": frame_num,
                "frame_time": data["frame_time"],
                "offset_seconds": data["offset_seconds"],
                "occupied_slots": occupied,
                "free_slots": free,
                "occupancy_rate": round(occupancy_rate, 2),
                "total_vehicles": data["total_vehicles"],
            }
        )

    # Calculate slot-level statistics
    slot_occupancy = {slot_id: 0 for slot_id in slot_polygons.keys()}

    for data in frame_data.values():
        for slot_id in data["occupied_slots"]:
            slot_occupancy[slot_id] += 1

    total_frames = len(unique_frames)
    slot_statistics = []

    for slot in parking_slots:
        occupied_frames = slot_occupancy.get(slot.id, 0)
        occupancy_rate = occupied_frames / total_frames if total_frames > 0 else 0

        slot_statistics.append(
            {
                "slot_id": str(slot.id),
                "slot_name": slot.name,
                "occupied_frames": occupied_frames,
                "total_frames": total_frames,
                "occupancy_rate": round(occupancy_rate, 2),
                "status": (
                    "busy"
                    if occupancy_rate > 0.7
                    else ("moderate" if occupancy_rate > 0.3 else "free")
                ),
            }
        )

    # Sort by occupancy rate
    slot_statistics.sort(key=lambda x: x["occupancy_rate"], reverse=True)

    # Calculate summary
    avg_occupancy = sum(occupancy_rates) / len(occupancy_rates) if occupancy_rates else 0
    peak_occupancy = max(occupancy_rates) if occupancy_rates else 0

    # Get parking lots for aggregation
    lots_query = select(ParkingLot).where(ParkingLot.camera_id == video.camera_id)
    lots_result = await db.execute(lots_query)
    parking_lots = lots_result.scalars().all()

    # Map slots to lots using containment check
    slot_to_lot_map = {}
    lot_polygons = {lot.id: (polygon_from_geojson(lot.polygon), lot.name) for lot in parking_lots}

    for slot in parking_slots:
        slot_poly = polygon_from_geojson(slot.polygon)

        # Check which lot contains this slot (at least 50% overlap)
        for lot_id, (lot_poly, lot_name) in lot_polygons.items():
            if check_containment(slot_poly, lot_poly, threshold=0.5):
                slot_to_lot_map[slot.id] = lot_id
                break  # Assign to first matching lot

    # Aggregate slot statistics by lots
    lot_statistics = []
    if parking_lots:
        lot_occupancy = {lot.id: {"occupied_frames": 0, "total_slots": 0} for lot in parking_lots}

        for slot in parking_slots:
            lot_id = slot_to_lot_map.get(slot.id)
            if lot_id:
                lot_occupancy[lot_id]["total_slots"] += 1
                occupied_frames = slot_occupancy.get(slot.id, 0)
                lot_occupancy[lot_id]["occupied_frames"] += occupied_frames

        for lot in parking_lots:
            lot_data = lot_occupancy[lot.id]
            total_slots_in_lot = lot_data["total_slots"]

            if total_slots_in_lot > 0:
                # Calculate average occupancy rate across all slots in this lot
                avg_occupied_frames = lot_data["occupied_frames"] / total_slots_in_lot
                occupancy_rate = avg_occupied_frames / total_frames if total_frames > 0 else 0

                lot_statistics.append(
                    {
                        "lot_id": str(lot.id),
                        "lot_name": lot.name,
                        "total_slots": total_slots_in_lot,
                        "occupancy_rate": round(occupancy_rate, 2),
                        "status": (
                            "busy"
                            if occupancy_rate > 0.7
                            else ("moderate" if occupancy_rate > 0.3 else "free")
                        ),
                    }
                )

        lot_statistics.sort(key=lambda x: x["occupancy_rate"], reverse=True)

    return {
        "video_id": str(video_id),
        "video_filename": video.filename,
        "processed": video.processed,
        "duration_seconds": video.duration_seconds,
        "fps": video.fps,
        "total_detections": total_detections,
        "frames_analyzed": total_frames,
        "summary": {
            "total_vehicles_detected": total_detections,
            "average_occupancy_rate": round(avg_occupancy, 2),
            "peak_occupancy_rate": round(peak_occupancy, 2),
            "total_parking_slots": total_slots,
            "total_parking_lots": len(parking_lots),
            "average_vehicles_per_frame": (
                round(total_detections / total_frames, 1) if total_frames > 0 else 0
            ),
        },
        "vehicle_breakdown": vehicle_breakdown,
        "occupancy_timeline": (
            occupancy_timeline[-50:] if len(occupancy_timeline) > 50 else occupancy_timeline
        ),  # Last 50 frames
        "slot_statistics": slot_statistics,
        "lot_statistics": lot_statistics,  # Aggregated by parking lots
    }
