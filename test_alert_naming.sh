#!/bin/bash

# Test script to check alert image naming format
echo "Testing alert image naming format..."

# Create a timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CAMERA_ID="CAM_TEST"

# Create a test source image
SOURCE_PATH="/tmp/source_${TIMESTAMP}_${CAMERA_ID}.jpg"
echo "Creating test source image: $SOURCE_PATH"

# Create a simple test image (a black square)
docker exec -it yolo_pose_api-alert-logic-1 /bin/bash -c "python3 -c \"import cv2, numpy as np; img = np.zeros((300, 300, 3), dtype=np.uint8); cv2.imwrite('/app/output_image/source_${TIMESTAMP}_${CAMERA_ID}.jpg', img)\""

# Create test pose data (simplified for testing)
POSE_DATA="[[100, 100, 1, 150, 80, 1, 200, 120, 1]]"

echo "Posting test alert to alert service..."
RESPONSE=$(curl -s -X POST http://localhost:8012/alert \
    -F "camera_id=${CAMERA_ID}" \
    -F "detection_type=poses" \
    -F "date_time=$(date -Iseconds)" \
    -F "image_source=/app/output_image/source_${TIMESTAMP}_${CAMERA_ID}.jpg" \
    -F "poses=${POSE_DATA}")

echo "Response from alert service:"
echo "$RESPONSE" | python3 -m json.tool

# Check database for the alert
echo "Checking database for the alert..."
docker exec yolo_pose_api-db-1 psql -U postgres -d camera_system -c "SELECT id, camera_id, alert_type_id, alert_datetime, alert_image_path FROM alerts ORDER BY alert_datetime DESC LIMIT 1;"

# List files in output directory to verify naming
echo "Files in output directory:"
docker exec yolo_pose_api-alert-logic-1 ls -la /app/output_image/

echo "Test complete."
