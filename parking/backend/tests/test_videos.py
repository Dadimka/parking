"""Tests for video endpoints."""

import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera, Video


@pytest.mark.asyncio
async def test_list_videos(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing videos."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for videos")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create test videos
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

    response = await async_client.get("/api/v1/videos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_video(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific video."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for video")
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

    response = await async_client.get(f"/api/v1/videos/{video.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_video.mp4"
    assert data["id"] == str(video.id)


@pytest.mark.asyncio
async def test_update_video(async_client: AsyncClient, db_session: AsyncSession):
    """Test updating a video."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for video")
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

    new_start_time = datetime.now()
    response = await async_client.patch(
        f"/api/v1/videos/{video.id}",
        json={"video_start_time": new_start_time.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_start_time"] is not None


@pytest.mark.asyncio
async def test_delete_video(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a video."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for video")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create a video
    video = Video(
        camera_id=camera.id,
        filename="to_delete.mp4",
        duration_seconds=60.0,
        fps=30,
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)

    video_id = video.id

    response = await async_client.delete(f"/api/v1/videos/{video_id}")
    assert response.status_code == 204

    # Verify video is deleted
    response = await async_client.get(f"/api/v1/videos/{video_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_videos_by_camera(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing videos for a specific camera."""
    # Create cameras
    camera1 = Camera(name="Camera 1", description="First camera")
    camera2 = Camera(name="Camera 2", description="Second camera")
    db_session.add_all([camera1, camera2])
    await db_session.commit()
    await db_session.refresh(camera1)

    # Create videos for camera1
    video1 = Video(
        camera_id=camera1.id,
        filename="video1.mp4",
        duration_seconds=60.0,
        fps=30,
    )
    video2 = Video(
        camera_id=camera1.id,
        filename="video2.mp4",
        duration_seconds=120.0,
        fps=30,
    )
    # Create video for camera2
    video3 = Video(
        camera_id=camera2.id,
        filename="video3.mp4",
        duration_seconds=90.0,
        fps=30,
    )
    db_session.add_all([video1, video2, video3])
    await db_session.commit()

    # Get videos for camera1
    response = await async_client.get(f"/api/v1/videos/?camera_id={camera1.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(v["camera_id"] == str(camera1.id) for v in data)
