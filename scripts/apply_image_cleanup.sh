#!/bin/bash

# =========================================================
#  APPLY IMAGE CLEANUP CHANGES - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  APPLYING IMAGE CLEANUP FUNCTIONALITY"
echo "==========================================================="

echo "Step 1: Stopping the alert-logic service..."
docker-compose stop alert-logic

echo "Step 2: Rebuilding the alert-logic service with cleanup functionality..."
docker-compose build alert-logic

echo "Step 3: Starting the alert-logic service..."
docker-compose up -d alert-logic

echo "Step 4: Checking if alert-logic service is running..."
sleep 3
SERVICE_STATUS=$(docker-compose ps alert-logic | grep "Up")
if [ -n "$SERVICE_STATUS" ]; then
    echo "Success! The alert-logic service is now running with image cleanup functionality."
else
    echo "Warning: The alert-logic service might not have started correctly."
    docker-compose logs alert-logic | tail -n 20
fi

echo ""
echo "==========================================================="
echo "  IMAGE CLEANUP FUNCTIONALITY ADDED"
echo "==========================================================="
echo ""
echo "New Features:"
echo "1. Automatic cleanup of unused images (runs every 60 minutes)"
echo "2. Removes source and overlay images without corresponding alerts"
echo "3. Only affects images older than 30 minutes"
echo "4. New API endpoint: POST /cleanup for manual cleanup"
echo ""
echo "To manually test the cleanup functionality:"
echo "  ./scripts/test_cleanup.sh"
echo ""
echo "To manually trigger the cleanup via API:"
echo "  curl -X POST \"http://localhost:8012/cleanup?min_age_minutes=30&dry_run=true\""
echo "==========================================================="
