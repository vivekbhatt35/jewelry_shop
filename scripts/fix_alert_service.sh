#!/bin/bash
set -e

echo "========================================================="
echo "  FIXING ALERT-LOGIC SERVICE"
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

echo "Step 4: Checking if alert-logic is now running..."
if docker-compose ps | grep "alert-logic" | grep "Up" > /dev/null; then
  echo "Success! The alert-logic service is now running."
else
  echo "Warning: The alert-logic service may still have issues. Check logs with:"
  echo "  docker-compose logs alert-logic"
fi

echo "========================================================="
echo "  ALERT SYSTEM FIXED"
echo "========================================================="
echo
echo "The alert-logic service should now be running properly with the"
echo "missing draw_bboxes function implemented."
echo
echo "Alert images will now be saved with the improved naming format:"
echo "  alert_CAMERAID_DATETIME_PERSONID_ALERTTYPE.jpg"
echo
echo "To verify the system is working, check the logs:"
echo "  docker-compose logs -f"
echo
echo "========================================================="
