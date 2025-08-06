#!/bin/bash
set -e

echo "========================================================="
echo "  APPLYING ALERT IMAGE NAMING & VIDEO LOOP FIXES"
echo "========================================================="
echo

echo "Step 1: Stopping all running containers..."
docker-compose down || true
sleep 3

echo "Step 2: Building and starting all services..."
docker-compose build
docker-compose up -d

echo "Step 3: Waiting for services to initialize..."
sleep 10

echo "========================================================="
echo "  CHANGES APPLIED SUCCESSFULLY"
echo "========================================================="
echo
echo "The following improvements have been implemented:"
echo
echo "1. Alert Image Naming Improvement:"
echo "   - Alert images now include camera_id, datetime, person ID, and alert type"
echo "   - Format: alert_CAMERAID_DATETIME_PERSONID_ALERTTYPE.jpg"
echo
echo "2. Video Looping Control:"
echo "   - Added 'loop_video' setting in camera configuration"
echo "   - Set to 'false' to make videos play only once"
echo "   - Set to 'true' to make videos loop continuously"
echo
echo "Current configuration for CAM_002 has loop_video=false"
echo "You can modify this setting via the API or config file."
echo
echo "To verify the changes, check logs using:"
echo "  docker-compose logs -f camera-manager"
echo
echo "========================================================="
