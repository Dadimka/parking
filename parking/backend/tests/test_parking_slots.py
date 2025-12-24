"""Tests for parking slot endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera, ParkingSlot


@pytest.mark.asyncio
async def test_create_parking_slot(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating a parking slot."""
    # Create a camera first
    camera = Camera(name="Test Camera", description="Camera for parking slot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
    }

    response = await async_client.post(
        "/api/v1/parking-slots/",
        json={
            "camera_id": str(camera.id),
            "name": "Slot A1",
            "polygon": polygon_data,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Slot A1"
    assert data["camera_id"] == str(camera.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_parking_slots(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing parking slots."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking slots")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create test parking slots
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
    }

    slot1 = ParkingSlot(camera_id=camera.id, name="Slot A1", polygon=polygon_data)
    slot2 = ParkingSlot(camera_id=camera.id, name="Slot A2", polygon=polygon_data)
    db_session.add_all([slot1, slot2])
    await db_session.commit()

    response = await async_client.get("/api/v1/parking-slots/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_parking_slot(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific parking slot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking slot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create parking slot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
    }
    parking_slot = ParkingSlot(camera_id=camera.id, name="Test Slot", polygon=polygon_data)
    db_session.add(parking_slot)
    await db_session.commit()
    await db_session.refresh(parking_slot)

    response = await async_client.get(f"/api/v1/parking-slots/{parking_slot.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Slot"
    assert data["id"] == str(parking_slot.id)


@pytest.mark.asyncio
async def test_update_parking_slot(async_client: AsyncClient, db_session: AsyncSession):
    """Test updating a parking slot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking slot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create parking slot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
    }
    parking_slot = ParkingSlot(camera_id=camera.id, name="Old Slot", polygon=polygon_data)
    db_session.add(parking_slot)
    await db_session.commit()
    await db_session.refresh(parking_slot)

    response = await async_client.patch(
        f"/api/v1/parking-slots/{parking_slot.id}",
        json={"name": "New Slot"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Slot"


@pytest.mark.asyncio
async def test_delete_parking_slot(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a parking slot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking slot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create parking slot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
    }
    parking_slot = ParkingSlot(camera_id=camera.id, name="To Delete", polygon=polygon_data)
    db_session.add(parking_slot)
    await db_session.commit()
    await db_session.refresh(parking_slot)

    slot_id = parking_slot.id

    response = await async_client.delete(f"/api/v1/parking-slots/{slot_id}")
    assert response.status_code == 204

    # Verify parking slot is deleted
    response = await async_client.get(f"/api/v1/parking-slots/{slot_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_parking_slot_invalid_camera(async_client: AsyncClient):
    """Test creating a parking slot with non-existent camera."""
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
    }

    response = await async_client.post(
        "/api/v1/parking-slots/",
        json={
            "camera_id": "00000000-0000-0000-0000-000000000000",
            "name": "Slot A1",
            "polygon": polygon_data,
        },
    )
    assert response.status_code == 404
