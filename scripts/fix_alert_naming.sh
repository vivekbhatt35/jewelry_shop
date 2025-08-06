#!/bin/bash

echo "==========================================================="
echo "  FIXING ALERT IMAGE NAMING"
echo "==========================================================="

echo "Step 1: Stopping the alert-logic service..."
docker-compose stop alert-logic

echo "Step 2: Rebuilding the alert-logic service with improved naming..."
docker-compose build alert-logic

echo "Step 3: Starting the alert-logic service..."
docker-compose up -d alert-logic

echo "Step 4: Checking if alert-logic service is running..."
sleep 3
SERVICE_STATUS=$(docker-compose ps alert-logic | grep "Up")
if [ -n "$SERVICE_STATUS" ]; then
    echo "Success! The alert-logic service is now running with simplified alert naming."
else
    echo "Warning: The alert-logic service might not have started correctly."
    docker-compose logs alert-logic | tail -n 20
fi

echo ""
echo "Step 5: Restarting the camera-manager to process video again..."
docker-compose restart camera-manager

echo "Step 6: Waiting for new alerts to be generated (15 seconds)..."
sleep 15

echo "Step 7: Checking for alert images with new naming format..."
ls -la output_image/alert_CAM* | head -n 5

echo ""
echo "==========================================================="
echo "  ALERT NAMING IMPROVED"
echo "==========================================================="
echo ""
echo "The alert image naming format has been simplified:"
echo "  OLD: alert_CAMERAID_FULLDATETIME_PERSONID_ALERTTYPE.jpg"
echo "  NEW: alert_CAMERAID_HHMMSS_ALERTTYPE.jpg"
echo ""
echo "Benefits:"
echo "1. Shorter, more readable filenames"
echo "2. Removed timezone information"
echo "3. Removed unnecessary person ID"
echo "4. Still maintains key information: camera, time, alert type"
echo ""
echo "You can run this script again to reprocess the video and generate more alerts."
echo "==========================================================="
