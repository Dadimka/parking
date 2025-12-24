"""Configuration settings for the application."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/parking_monitoring"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/parking_monitoring"

    # Application
    APP_NAME: str = "Parking Monitoring System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Storage
    VIDEO_STORAGE_PATH: Path = Path("./data/videos")
    FRAME_STORAGE_PATH: Path = Path("./data/frames")

    # YOLO Model
    YOLO_MODEL_PATH: Optional[str] = "./models/visdrone-best.pt"

    # Video Processing
    FRAME_STRIDE: int = 30
    IOU_THRESHOLD: float = 0.3
    CONFIDENCE_THRESHOLD: float = 0.5

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure storage directories exist
        self.VIDEO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        self.FRAME_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


settings = Settings()
