"""Tests for parking lot endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera, ParkingLot


@pytest.mark.asyncio
async def test_create_parking_lot(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating a parking lot."""
    # Create a camera first
    camera = Camera(name="Test Camera", description="Camera for parking lot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }

    response = await async_client.post(
        "/api/v1/parking-lots/",
        json={
            "camera_id": str(camera.id),
            "name": "Parking Lot A",
            "polygon": polygon_data,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Parking Lot A"
    assert data["camera_id"] == str(camera.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_parking_lots(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing parking lots."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking lots")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create test parking lots
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }

    lot1 = ParkingLot(camera_id=camera.id, name="Lot A", polygon=polygon_data)
    lot2 = ParkingLot(camera_id=camera.id, name="Lot B", polygon=polygon_data)
    db_session.add_all([lot1, lot2])
    await db_session.commit()

    response = await async_client.get("/api/v1/parking-lots/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_parking_lot(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific parking lot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking lot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(camera_id=camera.id, name="Test Lot", polygon=polygon_data)
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    response = await async_client.get(f"/api/v1/parking-lots/{parking_lot.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Lot"
    assert data["id"] == str(parking_lot.id)


@pytest.mark.asyncio
async def test_update_parking_lot(async_client: AsyncClient, db_session: AsyncSession):
    """Test updating a parking lot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking lot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(camera_id=camera.id, name="Old Name", polygon=polygon_data)
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    response = await async_client.patch(
        f"/api/v1/parking-lots/{parking_lot.id}",
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_parking_lot(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a parking lot."""
    # Create a camera
    camera = Camera(name="Test Camera", description="Camera for parking lot")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    # Create parking lot
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }
    parking_lot = ParkingLot(camera_id=camera.id, name="To Delete", polygon=polygon_data)
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)

    lot_id = parking_lot.id

    response = await async_client.delete(f"/api/v1/parking-lots/{lot_id}")
    assert response.status_code == 204

    # Verify parking lot is deleted
    response = await async_client.get(f"/api/v1/parking-lots/{lot_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_parking_lot_invalid_camera(async_client: AsyncClient):
    """Test creating a parking lot with non-existent camera."""
    polygon_data = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
    }

    response = await async_client.post(
        "/api/v1/parking-lots/",
        json={
            "camera_id": "00000000-0000-0000-0000-000000000000",
            "name": "Parking Lot A",
            "polygon": polygon_data,
        },
    )
    assert response.status_code == 404
