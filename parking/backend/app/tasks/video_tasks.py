"""Video processing tasks using TaskIQ and YOLO."""

import cv2
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from shapely.geometry import Polygon, box
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from ultralytics import YOLO

from app.config import settings
from app.db.models import Video, ParkingLot, ParkingSlot, OccupancyEvent, Detection
from app.tasks.broker import broker

logger = logging.getLogger(__name__)


# Global YOLO model (loaded once per worker)
_yolo_model: Optional[YOLO] = None


def get_yolo_model() -> YOLO:
    """Get or initialize YOLO model."""
    global _yolo_model
    if _yolo_model is None:
        model_path = settings.YOLO_MODEL_PATH or "yolo11n.pt"
        logger.info(f"Loading YOLO model from: {model_path}")
        _yolo_model = YOLO(model_path)
        logger.info("YOLO model loaded successfully")
    return _yolo_model


def polygon_from_geojson(geojson_data: dict) -> Polygon:
    """Convert GeoJSON polygon to Shapely Polygon."""
    coordinates = geojson_data.get("coordinates", [[]])[0]
    return Polygon([(pt[0], pt[1]) for pt in coordinates])


def bbox_to_polygon(x: float, y: float, w: float, h: float) -> Polygon:
    """Convert bbox to Shapely Polygon."""
    return box(x, y, x + w, y + h)


def calculate_iou(poly1: Polygon, poly2: Polygon) -> float:
    """Calculate Intersection over Union between two polygons."""
    try:
        intersection = poly1.intersection(poly2).area
        union = poly1.union(poly2).area
        return intersection / union if union > 0 else 0.0
    except Exception:
        return 0.0


class OccupancyTracker:
    """Track occupancy status with temporal smoothing."""

    def __init__(self, confirm_frames: int = 3):
        self.confirm_frames = confirm_frames
        self.state: Dict[UUID, List[bool]] = {}

    def update(self, slot_id: UUID, is_occupied: bool) -> Optional[str]:
        """
        Update slot state and return status if confirmed change occurs.
        Returns: 'occupied', 'free', or None if no confirmed change
        """
        if slot_id not in self.state:
            self.state[slot_id] = []

        self.state[slot_id].append(is_occupied)

        if len(self.state[slot_id]) > self.confirm_frames:
            self.state[slot_id].pop(0)

        if len(self.state[slot_id]) == self.confirm_frames:
            if all(self.state[slot_id]):
                return "occupied"
            elif not any(self.state[slot_id]):
                return "free"

        return None


@broker.task(retry_on_error=True, max_retries=2)
async def process_video_task(
    video_id: str,
    frame_stride: Optional[int] = None,
    iou_threshold: Optional[float] = None,
    confidence_threshold: Optional[float] = None,
) -> Dict:
    """
    Process a video file and detect parking occupancy.

    Args:
        video_id: UUID of the video record
        frame_stride: Process every Nth frame
        iou_threshold: Minimum IoU between detection and parking slot
        confidence_threshold: Minimum YOLO detection confidence

    Returns:
        Dictionary with processing results and statistics
    """
    # Use settings defaults if not provided
    frame_stride = frame_stride or settings.FRAME_STRIDE
    iou_threshold = iou_threshold or settings.IOU_THRESHOLD
    confidence_threshold = confidence_threshold or settings.CONFIDENCE_THRESHOLD

    # Create async database session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    video_uuid = UUID(video_id)

    async with async_session() as session:
        # Get video record
        result = await session.execute(select(Video).where(Video.id == video_uuid))
        video = result.scalar_one_or_none()

        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Update processing status
        video.processing_started_at = datetime.utcnow()
        await session.commit()

        try:
            # Get parking lots and slots for this camera
            lots_result = await session.execute(
                select(ParkingLot).where(ParkingLot.camera_id == video.camera_id)
            )
            parking_lots = lots_result.scalars().all()

            slots_result = await session.execute(
                select(ParkingSlot).where(ParkingSlot.camera_id == video.camera_id)
            )
            parking_slots = slots_result.scalars().all()

            if not parking_slots:
                raise ValueError("No parking slots defined for this camera")

            # Convert to Shapely polygons
            slot_polygons = {slot.id: polygon_from_geojson(slot.polygon) for slot in parking_slots}

            # Process video
            events_created = await _process_video_frames(
                session=session,
                video=video,
                parking_lots=parking_lots,
                parking_slots=parking_slots,
                slot_polygons=slot_polygons,
                frame_stride=frame_stride,
                iou_threshold=iou_threshold,
                confidence_threshold=confidence_threshold,
            )

            # Update video record
            video.processed = True
            video.processing_finished_at = datetime.utcnow()
            await session.commit()

            processing_time = (
                video.processing_finished_at - video.processing_started_at
            ).total_seconds()

            return {
                "success": True,
                "video_id": str(video_id),
                "events_created": events_created,
                "processing_time": processing_time,
            }

        except Exception as e:
            video.processed = False
            video.processing_error = str(e)
            video.processing_finished_at = datetime.utcnow()
            await session.commit()
            raise
        finally:
            await engine.dispose()


async def _process_video_frames(
    session: AsyncSession,
    video: Video,
    parking_lots: List[ParkingLot],
    parking_slots: List[ParkingSlot],
    slot_polygons: Dict[UUID, Polygon],
    frame_stride: int,
    iou_threshold: float,
    confidence_threshold: float,
) -> int:
    """Process video frames and create occupancy events."""

    video_path = settings.VIDEO_STORAGE_PATH / video.filename
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Update video metadata
    video.fps = fps
    video.duration_seconds = total_frames / fps if fps > 0 else 0

    # Determine video start time
    video_start_time = video.video_start_time or video.upload_time

    # Initialize YOLO model
    model = get_yolo_model()

    # Get frame dimensions for normalization
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    detections_created = 0
    frame_idx = 0

    # Vehicle class IDs and names in VisDrone dataset
    vehicle_classes = {
        0: "pedestrian",
        1: "people",
        2: "bicycle",
        3: "car",
        4: "van",
        5: "truck",
        6: "tricycle",
        7: "awning-tricycle",
        8: "bus",
        9: "motor",
    }

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Only process every Nth frame
            if frame_idx % frame_stride != 0:
                frame_idx += 1
                continue

            # Calculate timestamp
            offset_seconds = frame_idx / fps if fps > 0 else 0
            frame_time = video_start_time + timedelta(seconds=offset_seconds)

            # Run YOLO detection
            results = model(frame, verbose=True)

            # Process detections and save raw data
            for result in results:
                boxes = result.boxes
                for box_data in boxes:
                    # Get box coordinates and confidence
                    x1, y1, x2, y2 = box_data.xyxy[0].cpu().numpy()
                    conf = float(box_data.conf[0])
                    cls = int(box_data.cls[0])

                    # Only process vehicles with sufficient confidence
                    if cls not in vehicle_classes or conf < confidence_threshold:
                        continue

                    # Get track_id if available (for YOLO tracking mode)
                    track_id = None
                    if hasattr(box_data, "id") and box_data.id is not None:
                        track_id = int(box_data.id[0])

                    # Create detection record with raw YOLO data
                    detection = Detection(
                        video_id=video.id,
                        camera_id=video.camera_id,
                        frame_number=frame_idx,
                        frame_time=frame_time,
                        offset_seconds=offset_seconds,
                        class_id=cls,
                        class_name=vehicle_classes[cls],
                        confidence=conf,
                        bbox={
                            "x1": float(x1),
                            "y1": float(y1),
                            "x2": float(x2),
                            "y2": float(y2),
                        },
                        bbox_normalized={
                            "x1": float(x1 / frame_width),
                            "y1": float(y1 / frame_height),
                            "x2": float(x2 / frame_width),
                            "y2": float(y2 / frame_height),
                        },
                        track_id=track_id,
                    )
                    session.add(detection)
                    detections_created += 1

            # Commit every 100 frames to avoid memory issues
            if frame_idx % (frame_stride * 100) == 0:
                await session.commit()
                logger.info(
                    f"Processed frame {frame_idx}/{total_frames}, detections: {detections_created}"
                )

            frame_idx += 1

        # Final commit
        await session.commit()

        logger.info(
            f"Frame processing completed. "
            f"Total frames: {total_frames}, Processed frames: {frame_idx // frame_stride}, "
            f"Detections created: {detections_created}"
        )

    finally:
        cap.release()

    return detections_created
