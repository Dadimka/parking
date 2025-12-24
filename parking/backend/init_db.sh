#!/bin/bash

# Script to initialize the database and run migrations

echo "Waiting for PostgreSQL to start..."
sleep 5

echo "Running database migrations..."
alembic upgrade head

echo "Database initialization complete!"

