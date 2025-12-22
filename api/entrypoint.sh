#!/bin/bash
# Docker entrypoint script for the API service
# Runs database migrations before starting the application

set -e

echo "Running database migrations..."
python -m alembic upgrade head

echo "Starting API server..."
exec "$@"
