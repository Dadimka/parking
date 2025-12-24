"""TaskIQ broker configuration."""

from taskiq_postgresql import PostgresqlBroker

from app.config import settings

# Create PostgreSQL broker
broker = PostgresqlBroker(
    dsn=settings.SYNC_DATABASE_URL,
)


async def startup_broker():
    """Initialize broker on application startup."""
    if not broker.is_worker_process:
        await broker.startup()


async def shutdown_broker():
    """Shutdown broker on application shutdown."""
    if not broker.is_worker_process:
        await broker.shutdown()
