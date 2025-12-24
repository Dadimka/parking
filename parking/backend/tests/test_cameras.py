"""Tests for camera endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera


@pytest.mark.asyncio
async def test_create_camera(async_client: AsyncClient):
    """Test creating a camera."""
    response = await async_client.post(
        "/api/v1/cameras/",
        json={
            "name": "Test Camera 1",
            "description": "Test camera description",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Camera 1"
    assert data["description"] == "Test camera description"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_cameras(async_client: AsyncClient, db_session: AsyncSession):
    """Test listing cameras."""
    # Create test cameras
    camera1 = Camera(name="Camera 1", description="First camera")
    camera2 = Camera(name="Camera 2", description="Second camera")
    db_session.add_all([camera1, camera2])
    await db_session.commit()

    response = await async_client.get("/api/v1/cameras/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_camera(async_client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific camera."""
    # Create test camera
    camera = Camera(name="Test Camera", description="Test")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    response = await async_client.get(f"/api/v1/cameras/{camera.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Camera"
    assert data["id"] == str(camera.id)


@pytest.mark.asyncio
async def test_update_camera(async_client: AsyncClient, db_session: AsyncSession):
    """Test updating a camera."""
    # Create test camera
    camera = Camera(name="Old Name", description="Old description")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    response = await async_client.patch(
        f"/api/v1/cameras/{camera.id}",
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Old description"


@pytest.mark.asyncio
async def test_delete_camera(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a camera."""
    # Create test camera
    camera = Camera(name="To Delete", description="Will be deleted")
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)

    camera_id = camera.id

    response = await async_client.delete(f"/api/v1/cameras/{camera_id}")
    assert response.status_code == 204

    # Verify camera is deleted
    response = await async_client.get(f"/api/v1/cameras/{camera_id}")
    assert response.status_code == 404
