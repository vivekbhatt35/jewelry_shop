#!/bin/bash
set -e

echo "========================================================="
echo "  APPLYING FRAME EXTRACTION FIX"
echo "========================================================="
echo

echo "Step 1: Stopping all running containers..."
docker-compose down || true
sleep 3

echo "Step 2: Building and starting all services..."
docker-compose build camera-manager
docker-compose up -d

echo "Step 3: Waiting for services to initialize..."
sleep 10

echo "========================================================="
echo "  FRAME EXTRACTION FIX APPLIED"
echo "========================================================="
echo
echo "The camera manager now extracts frames at precise intervals based on video FPS."
echo "For video files, frames will be extracted exactly every N seconds according to"
echo "the extract_interval setting in the camera configuration file."
echo
echo "You can check logs to verify the frame extraction is working correctly:"
echo "  docker-compose logs -f camera-manager"
echo
echo "========================================================="
