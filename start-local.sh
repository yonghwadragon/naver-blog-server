#!/bin/bash
# Local development startup script

echo "Starting Naver Blog Automation Cloud Server..."

# Check if Docker is running
if ! docker --version > /dev/null 2>&1; then
    echo "Error: Docker is not installed or not running"
    exit 1
fi

# Check if docker-compose is available
if ! docker-compose --version > /dev/null 2>&1; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Start services
echo "Starting Redis, FastAPI server, and Celery worker..."
docker-compose up --build

echo "Services started!"
echo "FastAPI server: http://localhost:8000"
echo "Flower monitoring: http://localhost:5555"