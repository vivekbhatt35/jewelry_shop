#!/bin/bash
# Script to test weapon detection alerts with the weapon_detector.py script
# This will process the gun video and then restart the services with proper configuration

echo "Running weapon detector test..."
./weapon_detector.py videos/gun4_2.mp4 output_weapon_detection.mp4 --model detector_detections/models/yolo11m.pt --alert-dir output_image/weapon_alerts

echo "Stopping any running services..."
./stop_services.sh

echo "Starting services with improved weapon detection..."
docker-compose up -d

echo "Watching logs for alerts..."
docker-compose logs -f alert-logic

# Press Ctrl+C to stop viewing logs
