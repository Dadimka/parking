"""Tests for occupancy event endpoints."""

import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera, Video, ParkingLot, ParkingSlot, OccupancyEvent


@pytest.mark.asyncio
async def test_create_occupancy_event(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating an occupancy event."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for event")
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

    # Create parking lot and slot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(
        camera_id=camera.id,
        name="Lot A",
        polygon=polygon_data,
    )
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    parking_slot = ParkingSlot(
        camera_id=camera.id,
        name="Slot A1",
        polygon=polygon_data,
    )
    db_session.add(parking_slot)
    await db_session.commit()
    await db_session.refresh(parking_slot)

    bbox_data = {"x": 100, "y": 100, "w": 50, "h": 50}

    response = await async_client.post(
        "/api/v1/events/",
        json={
            "video_id": str(video.id),
            "camera_id": str(camera.id),
            "parking_lot_id": str(parking_lot.id),
            "parking_slot_id": str(parking_slot.id),
            "frame_time": datetime.now().isoformat(),
            "offset_seconds": 3.33,
            "bbox": bbox_data,
            "confidence": 0.95,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["confidence"] == 0.95
    assert data["video_id"] == str(video.id)
    assert data["parking_lot_id"] == str(parking_lot.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_occupancy_events(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing occupancy events."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for events")
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

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(
        camera_id=camera.id,
        name="Lot A",
        polygon=polygon_data,
    )
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    # Create test events
    event1 = OccupancyEvent(
        video_id=video.id,
        camera_id=camera.id,
        parking_lot_id=parking_lot.id,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        confidence=0.95,
    )
    event2 = OccupancyEvent(
        video_id=video.id,
        camera_id=camera.id,
        parking_lot_id=parking_lot.id,
        frame_time=datetime.now(),
        offset_seconds=6.66,
        confidence=0.90,
    )
    db_session.add_all([event1, event2])
    await db_session.commit()

    response = await async_client.get("/api/v1/events/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_occupancy_event(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific occupancy event."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for event")
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

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(
        camera_id=camera.id,
        name="Lot A",
        polygon=polygon_data,
    )
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    # Create event
    event = OccupancyEvent(
        video_id=video.id,
        camera_id=camera.id,
        parking_lot_id=parking_lot.id,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        confidence=0.95,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    response = await async_client.get(f"/api/v1/events/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(event.id)


@pytest.mark.asyncio
async def test_list_events_by_parking_lot(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing events for a specific parking lot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for events")
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

    # Create parking lots
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    lot1 = ParkingLot(
        camera_id=camera.id,
        name="Lot A",
        polygon=polygon_data,
    )
    lot2 = ParkingLot(
        camera_id=camera.id,
        name="Lot B",
        polygon=polygon_data,
    )
    db_session.add_all([lot1, lot2])
    await db_session.commit()
    await db_session.refresh(lot1)

    # Create events for lot1
    event1 = OccupancyEvent(
        video_id=video.id,
        camera_id=camera.id,
        parking_lot_id=lot1.id,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        confidence=0.95,
    )
    event2 = OccupancyEvent(
        video_id=video.id,
        camera_id=camera.id,
        parking_lot_id=lot1.id,
        frame_time=datetime.now(),
        offset_seconds=6.66,
        confidence=0.90,
    )
    db_session.add_all([event1, event2])
    await db_session.commit()

    # Get events for lot1
    response = await async_client.get(f"/api/v1/events/?parking_lot_id={lot1.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(e["parking_lot_id"] == str(lot1.id) for e in data)


@pytest.mark.asyncio
async def test_delete_occupancy_event(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting an occupancy event."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for event")
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

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(
        camera_id=camera.id,
        name="Lot A",
        polygon=polygon_data,
    )
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    # Create event
    event = OccupancyEvent(
        video_id=video.id,
        camera_id=camera.id,
        parking_lot_id=parking_lot.id,
        frame_time=datetime.now(),
        offset_seconds=3.33,
        confidence=0.95,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    event_id = event.id

    response = await async_client.delete(f"/api/v1/events/{event_id}")
    assert response.status_code == 204

    # Verify event is deleted
    response = await async_client.get(f"/api/v1/events/{event_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_event_invalid_status(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating an event with invalid status."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for event")
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

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(
        camera_id=camera.id,
        name="Lot A",
        polygon=polygon_data,
    )
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    # Try to create event with invalid status
    response = await async_client.post(
        "/api/v1/events/",
        json={
            "video_id": str(video.id),
            "camera_id": str(camera.id),
            "parking_lot_id": str(parking_lot.id),
            "frame_time": datetime.now().isoformat(),
            "offset_seconds": 3.33,
            "status": "invalid_status",
        },
    )
    assert response.status_code == 422
