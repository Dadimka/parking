#!/usr/bin/env python
"""Test script to manually trigger video processing."""
import asyncio
import sys
from uuid import UUID

from app.config import settings
from app.tasks.video_tasks import process_video_task


async def test_process_video(video_id: str):
    """Test video processing task."""
    print(f"Testing video processing for video_id: {video_id}")
    print(f"Settings:")
    print(f"  - Frame stride: {settings.FRAME_STRIDE}")
    print(f"  - IoU threshold: {settings.IOU_THRESHOLD}")
    print(f"  - Confidence threshold: {settings.CONFIDENCE_THRESHOLD}")
    print(f"  - Video storage: {settings.VIDEO_STORAGE_PATH}")
    print()

    try:
        result = await process_video_task(video_id)
        print("Processing completed successfully!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_worker.py <video_id>")
        sys.exit(1)

    video_id = sys.argv[1]
    asyncio.run(test_process_video(video_id))
