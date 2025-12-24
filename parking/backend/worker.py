#!/usr/bin/env python
"""TaskIQ worker entry point."""

# Import broker and tasks to ensure they are registered
from app.tasks.broker import broker
from app.tasks.video_tasks import process_video_task

# The broker instance is now available at module level
# TaskIQ CLI will use this when running: taskiq worker worker:broker
