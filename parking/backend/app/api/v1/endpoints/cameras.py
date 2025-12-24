"""Camera endpoints."""

from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.config import settings
from app.db.models import Camera, ParkingLot, ParkingSlot, Video
from app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate, CameraWithStats

router = APIRouter()


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new camera."""
    camera = Camera(**camera_data.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return camera


@router.get("/", response_model=List[CameraWithStats])
async def list_cameras(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    """List all cameras with statistics."""
    result = await db.execute(
        select(Camera).offset(skip).limit(limit).order_by(Camera.created_at.desc())
    )
    cameras = result.scalars().all()

    # Get statistics for each camera
    cameras_with_stats = []
    for camera in cameras:
        videos_count = await db.scalar(
            select(func.count(Video.id)).where(Video.camera_id == camera.id)
        )
        lots_count = await db.scalar(
            select(func.count(ParkingLot.id)).where(ParkingLot.camera_id == camera.id)
        )
        slots_count = await db.scalar(
            select(func.count(ParkingSlot.id)).where(ParkingSlot.camera_id == camera.id)
        )

        camera_dict = {
            "id": camera.id,
            "name": camera.name,
            "description": camera.description,
            "preview_image": camera.preview_image,  # Добавлено!
            "created_at": camera.created_at,
            "updated_at": camera.updated_at,
            "total_videos": videos_count or 0,
            "total_parking_lots": lots_count or 0,
            "total_parking_slots": slots_count or 0,
        }
        cameras_with_stats.append(camera_dict)

    return cameras_with_stats


@router.get("/{camera_id}", response_model=CameraWithStats)
async def get_camera(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific camera by ID."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    # Get statistics
    videos_count = await db.scalar(select(func.count(Video.id)).where(Video.camera_id == camera.id))
    lots_count = await db.scalar(
        select(func.count(ParkingLot.id)).where(ParkingLot.camera_id == camera.id)
    )
    slots_count = await db.scalar(
        select(func.count(ParkingSlot.id)).where(ParkingSlot.camera_id == camera.id)
    )

    return {
        "id": camera.id,
        "name": camera.name,
        "description": camera.description,
        "preview_image": camera.preview_image,  # Добавлено!
        "created_at": camera.created_at,
        "updated_at": camera.updated_at,
        "total_videos": videos_count or 0,
        "total_parking_lots": lots_count or 0,
        "total_parking_slots": slots_count or 0,
    }


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: UUID,
    camera_data: CameraUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a camera."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    update_data = camera_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camera, field, value)

    await db.commit()
    await db.refresh(camera)
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a camera."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    await db.delete(camera)
    await db.commit()


# Preview image endpoints
FRAMES_DIR = settings.FRAME_STORAGE_PATH
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post(
    "/{camera_id}/preview", response_model=CameraResponse, status_code=status.HTTP_201_CREATED
)
async def upload_camera_preview(
    camera_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload a preview image for a camera."""
    print(f"\n{'='*80}")
    print(f"[DEBUG] UPLOAD PREVIEW CALLED!")
    print(f"[DEBUG] Camera ID: {camera_id}")
    print(f"[DEBUG] File name: {file.filename}")
    print(f"[DEBUG] File content type: {file.content_type}")
    print(f"{'='*80}\n")

    # Check if camera exists
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Create frames directory if it doesn't exist
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[DEBUG] FRAMES_DIR: {FRAMES_DIR}")
    print(f"[DEBUG] FRAMES_DIR exists: {FRAMES_DIR.exists()}")

    # Generate filename
    filename = f"camera_{camera_id}_preview{file_ext}"
    file_path = FRAMES_DIR / filename
    print(f"[DEBUG] Saving to: {file_path}")

    # Delete old preview if exists
    if camera.preview_image:
        old_file_path = FRAMES_DIR / camera.preview_image
        if old_file_path.exists():
            print(f"[DEBUG] Deleting old preview: {old_file_path}")
            old_file_path.unlink()

    # Save file
    try:
        contents = await file.read()
        print(f"[DEBUG] File size: {len(contents)} bytes")

        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB",
            )

        with open(file_path, "wb") as f:
            f.write(contents)

        print(f"[DEBUG] File saved successfully")
        print(f"[DEBUG] File exists after save: {file_path.exists()}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to save file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Update camera record
    camera.preview_image = filename
    print(f"[DEBUG] Updating camera.preview_image to: {filename}")
    await db.commit()
    await db.refresh(camera)
    print(f"[DEBUG] Camera after update: id={camera.id}, preview_image={camera.preview_image}")

    # Return updated camera
    return camera


@router.get("/{camera_id}/preview")
async def get_camera_preview(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get the preview image for a camera."""
    print(f"[DEBUG] GET preview for camera: {camera_id}")
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        print(f"[ERROR] Camera not found: {camera_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    print(f"[DEBUG] Camera.preview_image: {camera.preview_image}")

    if not camera.preview_image:
        print(f"[ERROR] No preview_image for camera: {camera_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preview image for this camera",
        )

    file_path = FRAMES_DIR / camera.preview_image
    print(f"[DEBUG] Looking for file at: {file_path}")
    print(f"[DEBUG] File exists: {file_path.exists()}")

    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview image file not found at {file_path}",
        )

    print(f"[DEBUG] Returning file: {file_path}")
    return FileResponse(file_path)


@router.delete("/{camera_id}/preview", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera_preview(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete the preview image for a camera."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id {camera_id} not found",
        )

    if camera.preview_image:
        file_path = FRAMES_DIR / camera.preview_image
        if file_path.exists():
            file_path.unlink()

        camera.preview_image = None
        await db.commit()
