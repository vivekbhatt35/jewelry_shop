#!/bin/bash

# Test script for database functionality

# Make sure the database is running
echo "Checking if the database is running..."
docker-compose ps db | grep "Up"
if [ $? -ne 0 ]; then
  echo "Starting database container..."
  docker-compose up -d db
  echo "Waiting for database to initialize..."
  sleep 10
fi

# Create a test camera configuration
echo "Creating a test camera configuration..."
curl -X POST -H "Content-Type: application/json" -d '{
  "camera_id": "CAM_001", 
  "camera_name": "Main Entrance", 
  "camera_url": "/app/videos/video5.mp4", 
  "camera_type": "file",
  "frame_interval": 1000,
  "detection_enabled": true,
  "pose_enabled": true,
  "notify_enabled": true
}' http://localhost:8010/cameras

# Test fetching camera configurations
echo "Fetching camera configurations..."
curl http://localhost:8010/cameras

# Test fetching alerts
echo "Fetching alerts..."
curl http://localhost:8012/alerts

echo "Database test completed"
