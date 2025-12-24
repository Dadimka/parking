"""ParkingSlot endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models import Camera, ParkingSlot
from app.schemas.parking_slot import ParkingSlotCreate, ParkingSlotResponse, ParkingSlotUpdate

router = APIRouter()


@router.post("/", response_model=ParkingSlotResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_slot(
    slot_data: ParkingSlotCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new parking slot."""
    # Verify camera exists
    result = await db.execute(select(Camera).where(Camera.id == slot_data.camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {slot_data.camera_id} not found",
        )

    slot = ParkingSlot(**slot_data.model_dump())
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.get("/", response_model=List[ParkingSlotResponse])
async def list_parking_slots(
    camera_id: Optional[UUID] = Query(None, description="Filter by camera ID"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    """List all parking slots, optionally filtered by camera."""
    query = select(ParkingSlot).offset(skip).limit(limit).order_by(ParkingSlot.created_at.desc())

    if camera_id:
        query = query.where(ParkingSlot.camera_id == camera_id)

    result = await db.execute(query)
    slots = result.scalars().all()
    return slots


@router.get("/{slot_id}", response_model=ParkingSlotResponse)
async def get_parking_slot(
    slot_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific parking slot by ID."""
    result = await db.execute(select(ParkingSlot).where(ParkingSlot.id == slot_id))
    slot = result.scalar_one_or_none()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking slot with id {slot_id} not found",
        )

    return slot


@router.patch("/{slot_id}", response_model=ParkingSlotResponse)
async def update_parking_slot(
    slot_id: UUID,
    slot_data: ParkingSlotUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a parking slot."""
    result = await db.execute(select(ParkingSlot).where(ParkingSlot.id == slot_id))
    slot = result.scalar_one_or_none()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking slot with id {slot_id} not found",
        )

    update_data = slot_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slot, field, value)

    await db.commit()
    await db.refresh(slot)
    return slot


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parking_slot(
    slot_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a parking slot."""
    result = await db.execute(select(ParkingSlot).where(ParkingSlot.id == slot_id))
    slot = result.scalar_one_or_none()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking slot with id {slot_id} not found",
        )

    await db.delete(slot)
    await db.commit()
