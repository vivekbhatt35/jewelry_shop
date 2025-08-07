#!/bin/bash

# Test script to create an actual hands-up alert to check naming
echo "Testing alert image naming with a known hands-up pose alert..."

# Create a timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CAMERA_ID="CAM_TEST"

# Create a test source image (black square)
docker exec -it yolo_pose_api-alert-logic-1 /bin/bash -c "python3 -c \"import cv2, numpy as np; img = np.zeros((300, 300, 3), dtype=np.uint8); cv2.imwrite('/app/output_image/source_${TIMESTAMP}_${CAMERA_ID}.jpg', img)\""

# Create test pose data specifically designed to trigger a hands-up alert
# Format: [nose_x, nose_y, nose_conf, l_eye_x, l_eye_y, l_eye_conf, r_eye_x, r_eye_y, r_eye_conf, l_ear_x, l_ear_y, l_ear_conf, r_ear_x, r_ear_y, r_ear_conf, l_shoulder_x, l_shoulder_y, l_shoulder_conf, r_shoulder_x, r_shoulder_y, r_shoulder_conf, l_elbow_x, l_elbow_y, l_elbow_conf, r_elbow_x, r_elbow_y, r_elbow_conf, l_wrist_x, l_wrist_y, l_wrist_conf, r_wrist_x, r_wrist_y, r_wrist_conf, l_hip_x, l_hip_y, l_hip_conf, r_hip_x, r_hip_y, r_hip_conf, l_knee_x, l_knee_y, l_knee_conf, r_knee_x, r_knee_y, r_knee_conf, l_ankle_x, l_ankle_y, l_ankle_conf, r_ankle_x, r_ankle_y, r_ankle_conf]

# Create a pose with hands definitely above head (hands above shoulders)
# Format simplified to key points needed for hands-up detection
POSE_DATA='[[150,100,1,140,90,1,160,90,1,130,95,1,170,95,1,130,150,1,170,150,1,130,120,1,170,120,1,130,80,1,170,80,1,130,200,1,170,200,1,130,250,1,170,250,1,130,290,1,170,290,1]]'

echo "Posting test alert with hands-up pose..."
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
docker exec yolo_pose_api-alert-logic-1 ls -la /app/output_image/ | grep -E "${CAMERA_ID}|alert_${CAMERA_ID}"

echo "Test complete."
