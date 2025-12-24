#!/bin/bash
set -e

# Entrypoint script for running migrations before starting the application

echo "================================"
echo "Parking Monitoring System"
echo "================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "Migrations completed successfully!"
else
    echo "Migrations failed!"
    exit 1
fi

# Execute the command passed to the entrypoint
echo "================================"
echo "Starting application: $1"
echo "================================"

case "$1" in
  api)
    echo "Starting FastAPI server..."
    exec python run.py
    ;;
  worker)
    echo "Starting TaskIQ worker..."
    exec taskiq worker worker:broker --workers 1
    ;;
  *)
    echo "Usage: entrypoint.sh {api|worker}"
    echo "Running custom command: $@"
    exec "$@"
    ;;
esac

