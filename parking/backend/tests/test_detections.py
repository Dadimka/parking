"""Tests for detection endpoints."""

from datetime import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera, Video, Detection


@pytest.mark.asyncio
async def test_get_detections(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing detections."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for detections")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create a video
    video = Video(
        camera_id=camera.id,
        filename="test_video.mp4",
        duration_seconds=60.0,
        fps=30,
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)

    # Create test detections
    bbox_data = {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
    bbox_normalized_data = {"x1": 0.1, "y1": 0.1, "x2": 0.2, "y2": 0.2}

    detection1 = Detection(
        video_id=video.id,
        camera_id=camera.id,
        frame_number=100,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        class_id=2,
        class_name="car",
        confidence=0.95,
        bbox=bbox_data,
        bbox_normalized=bbox_normalized_data,
        track_id=1,
    )
    detection2 = Detection(
        video_id=video.id,
        camera_id=camera.id,
        frame_number=200,
        frame_time=datetime.now(),
        offset_seconds=6.66,
        class_id=2,
        class_name="car",
        confidence=0.90,
        bbox=bbox_data,
        bbox_normalized=bbox_normalized_data,
        track_id=2,
    )
    db_session.add_all([detection1, detection2])
    await db_session.commit()

    response = await async_client.get("/api/v1/detections/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_detections_by_video(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing detections by video ID."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for detections")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create videos
    video1 = Video(
        camera_id=camera.id,
        filename="video1.mp4",
        duration_seconds=60.0,
        fps=30,
    )
    video2 = Video(
        camera_id=camera.id,
        filename="video2.mp4",
        duration_seconds=120.0,
        fps=30,
    )
    db_session.add_all([video1, video2])
    await db_session.commit()
    await db_session.refresh(video1)

    # Create detections for video1 only
    bbox_data = {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
    bbox_normalized_data = {"x1": 0.1, "y1": 0.1, "x2": 0.2, "y2": 0.2}

    detection1 = Detection(
        video_id=video1.id,
        camera_id=camera.id,
        frame_number=100,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        class_id=2,
        class_name="car",
        confidence=0.95,
        bbox=bbox_data,
        bbox_normalized=bbox_normalized_data,
        track_id=1,
    )

    db_session.add(detection1)
    await db_session.commit()

    # Get detections for video1
    response = await async_client.get(f"/api/v1/detections/video/{video1.id}/frames")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["frame_number"] == 100


@pytest.mark.asyncio
async def test_get_frame_detections(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting detections for a specific frame."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for detections")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create a video
    video = Video(
        camera_id=camera.id,
        filename="test_video.mp4",
        duration_seconds=60.0,
        fps=30,
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)

    # Create detections
    bbox_data = {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
    bbox_normalized_data = {"x1": 0.1, "y1": 0.1, "x2": 0.2, "y2": 0.2}

    detection1 = Detection(
        video_id=video.id,
        camera_id=camera.id,
        frame_number=100,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        class_id=2,
        class_name="car",
        confidence=0.95,
        bbox=bbox_data,
        bbox_normalized=bbox_normalized_data,
        track_id=1,
    )
    detection2 = Detection(
        video_id=video.id,
        camera_id=camera.id,
        frame_number=100,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        class_id=2,
        class_name="car",
        confidence=0.90,
        bbox=bbox_data,
        bbox_normalized=bbox_normalized_data,
        track_id=2,
    )
    db_session.add_all([detection1, detection2])
    await db_session.commit()

    response = await async_client.get(f"/api/v1/detections/video/{video.id}/frame/100")
    assert response.status_code == 200
    data = response.json()
    assert data["total_vehicles"] == 2
    assert len(data["detections"]) == 2
