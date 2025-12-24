"""OccupancyEvent endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models import OccupancyEvent, ParkingSlot
from app.schemas.occupancy_event import OccupancyEventResponse, OccupancyStats

router = APIRouter()


@router.get("/", response_model=List[OccupancyEventResponse])
async def list_occupancy_events(
    camera_id: Optional[UUID] = Query(None, description="Filter by camera ID"),
    video_id: Optional[UUID] = Query(None, description="Filter by video ID"),
    parking_lot_id: Optional[UUID] = Query(None, description="Filter by parking lot ID"),
    parking_slot_id: Optional[UUID] = Query(None, description="Filter by parking slot ID"),
    status_filter: Optional[str] = Query(
        None, description="Filter by status (occupied/free/unknown)"
    ),
    start_time: Optional[datetime] = Query(None, description="Filter events after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter events before this time"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    """List occupancy events with optional filters."""
    query = (
        select(OccupancyEvent).offset(skip).limit(limit).order_by(OccupancyEvent.frame_time.desc())
    )

    if camera_id:
        query = query.where(OccupancyEvent.camera_id == camera_id)
    if video_id:
        query = query.where(OccupancyEvent.video_id == video_id)
    if parking_lot_id:
        query = query.where(OccupancyEvent.parking_lot_id == parking_lot_id)
    if parking_slot_id:
        query = query.where(OccupancyEvent.parking_slot_id == parking_slot_id)
    if status_filter:
        query = query.where(OccupancyEvent.status == status_filter)
    if start_time:
        query = query.where(OccupancyEvent.frame_time >= start_time)
    if end_time:
        query = query.where(OccupancyEvent.frame_time <= end_time)

    result = await db.execute(query)
    events = result.scalars().all()
    return events


@router.get("/{event_id}", response_model=OccupancyEventResponse)
async def get_occupancy_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific occupancy event by ID."""
    result = await db.execute(select(OccupancyEvent).where(OccupancyEvent.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Occupancy event with id {event_id} not found",
        )

    return event


@router.get("/stats/current", response_model=OccupancyStats)
async def get_current_occupancy_stats(
    camera_id: Optional[UUID] = Query(None, description="Filter by camera ID"),
    parking_lot_id: Optional[UUID] = Query(None, description="Filter by parking lot ID"),
    db: AsyncSession = Depends(get_db_session),
):
    """Get current occupancy statistics."""
    # Get all parking slots
    slots_query = select(ParkingSlot)
    if camera_id:
        slots_query = slots_query.where(ParkingSlot.camera_id == camera_id)

    result = await db.execute(slots_query)
    slots = result.scalars().all()
    slot_ids = [slot.id for slot in slots]

    if not slot_ids:
        return OccupancyStats(
            total_slots=0,
            occupied_slots=0,
            free_slots=0,
            unknown_slots=0,
            occupancy_rate=0.0,
            timestamp=datetime.utcnow(),
        )

    # Get latest event for each slot
    # This is a simplified version - in production you'd want a more efficient query
    occupied = 0
    free = 0
    unknown = 0

    for slot_id in slot_ids:
        query = (
            select(OccupancyEvent)
            .where(OccupancyEvent.parking_slot_id == slot_id)
            .order_by(OccupancyEvent.frame_time.desc())
            .limit(1)
        )

        if parking_lot_id:
            query = query.where(OccupancyEvent.parking_lot_id == parking_lot_id)

        result = await db.execute(query)
        latest_event = result.scalar_one_or_none()

        if latest_event:
            if latest_event.status == "occupied":
                occupied += 1
            elif latest_event.status == "free":
                free += 1
            else:
                unknown += 1
        else:
            unknown += 1

    total = len(slot_ids)
    occupancy_rate = (occupied / total * 100) if total > 0 else 0.0

    return OccupancyStats(
        total_slots=total,
        occupied_slots=occupied,
        free_slots=free,
        unknown_slots=unknown,
        occupancy_rate=occupancy_rate,
        timestamp=datetime.utcnow(),
    )
