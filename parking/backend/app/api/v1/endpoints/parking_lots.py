"""ParkingLot endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models import Camera, ParkingLot
from app.schemas.parking_lot import ParkingLotCreate, ParkingLotResponse, ParkingLotUpdate

router = APIRouter()


@router.post("/", response_model=ParkingLotResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_lot(
    lot_data: ParkingLotCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new parking lot."""
    # Verify camera exists
    result = await db.execute(select(Camera).where(Camera.id == lot_data.camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {lot_data.camera_id} not found",
        )

    lot = ParkingLot(**lot_data.model_dump())
    db.add(lot)
    await db.commit()
    await db.refresh(lot)
    return lot


@router.get("/", response_model=List[ParkingLotResponse])
async def list_parking_lots(
    camera_id: Optional[UUID] = Query(None, description="Filter by camera ID"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    """List all parking lots, optionally filtered by camera."""
    query = select(ParkingLot).offset(skip).limit(limit).order_by(ParkingLot.created_at.desc())

    if camera_id:
        query = query.where(ParkingLot.camera_id == camera_id)

    result = await db.execute(query)
    lots = result.scalars().all()
    return lots


@router.get("/{lot_id}", response_model=ParkingLotResponse)
async def get_parking_lot(
    lot_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific parking lot by ID."""
    result = await db.execute(select(ParkingLot).where(ParkingLot.id == lot_id))
    lot = result.scalar_one_or_none()

    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking lot with id {lot_id} not found",
        )

    return lot


@router.patch("/{lot_id}", response_model=ParkingLotResponse)
async def update_parking_lot(
    lot_id: UUID,
    lot_data: ParkingLotUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a parking lot."""
    result = await db.execute(select(ParkingLot).where(ParkingLot.id == lot_id))
    lot = result.scalar_one_or_none()

    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking lot with id {lot_id} not found",
        )

    update_data = lot_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lot, field, value)

    await db.commit()
    await db.refresh(lot)
    return lot


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parking_lot(
    lot_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a parking lot."""
    result = await db.execute(select(ParkingLot).where(ParkingLot.id == lot_id))
    lot = result.scalar_one_or_none()

    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parking lot with id {lot_id} not found",
        )

    await db.delete(lot)
    await db.commit()
