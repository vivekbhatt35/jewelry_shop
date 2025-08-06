#!/bin/bash

echo "==========================================================="
echo "  FIXING HANDS UP DETECTION"
echo "==========================================================="

echo "Step 1: Stopping the alert-logic service..."
docker-compose stop alert-logic

echo "Step 2: Rebuilding the alert-logic service with improved hands-up detection..."
docker-compose build alert-logic

echo "Step 3: Starting the alert-logic service..."
docker-compose up -d alert-logic

echo "Step 4: Checking if alert-logic service is running..."
sleep 3
SERVICE_STATUS=$(docker-compose ps alert-logic | grep "Up")
if [ -n "$SERVICE_STATUS" ]; then
    echo "Success! The alert-logic service is now running with improved hands-up detection."
else
    echo "Warning: The alert-logic service might not have started correctly."
    docker-compose logs alert-logic | tail -n 20
fi

echo ""
echo "==========================================================="
echo "  DETECTION SENSITIVITY IMPROVED"
echo "==========================================================="
echo ""
echo "The following changes were made to improve hands-up detection:"
echo "1. Reduced alert throttling from 20 minutes to 10 seconds"
echo "2. Lowered hand height threshold from 40% to 15% of body height"
echo "3. Reduced confidence threshold from 0.85 to 0.6"
echo "4. Now allowing single hand to trigger alerts"
echo ""
echo "You should now see more frequent alerts for hands-up poses in the video."
echo "To view alerts, check the output_image directory for alert_*.jpg files"
echo "You can monitor logs with: docker-compose logs -f alert-logic"
echo "==========================================================="
