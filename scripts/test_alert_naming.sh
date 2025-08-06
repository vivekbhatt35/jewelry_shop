#!/bin/bash

echo "==========================================================="
echo "  TESTING ALERT IMAGE NAMING"
echo "==========================================================="

echo "Step 1: Creating test alert with hands up pose..."

# Find an existing image to use for testing
TEST_IMAGE=$(find output_image -name "source_*.png" | head -1)
if [ -z "$TEST_IMAGE" ]; then
    echo "Error: No source image found for testing!"
    exit 1
fi

echo "Using test image: $TEST_IMAGE"

# Get the current datetime in the format the system expects
DATETIME=$(date '+%Y-%m-%d %H:%M:%S')

# Create a pose JSON with realistic hands up pose data that will trigger the detection
# Important parameters:
# 1. Wrists are above shoulders (y-coordinates are lower)
# 2. Elbows are between shoulders and wrists
# 3. Height of wrists above shoulders > 40% of body height
POSE_JSON='[{"person_id":"test_person_123","keypoints":[
  {"name":"nose","x":400,"y":100,"v":0.9},
  {"name":"left_eye","x":380,"y":90,"v":0.9},
  {"name":"right_eye","x":420,"y":90,"v":0.9},
  {"name":"left_ear","x":370,"y":95,"v":0.9},
  {"name":"right_ear","x":430,"y":95,"v":0.9},
  {"name":"left_shoulder","x":350,"y":200,"v":0.9},
  {"name":"right_shoulder","x":450,"y":200,"v":0.9},
  {"name":"left_elbow","x":330,"y":150,"v":0.9},
  {"name":"right_elbow","x":470,"y":150,"v":0.9},
  {"name":"left_wrist","x":320,"y":80,"v":0.9},
  {"name":"right_wrist","x":480,"y":80,"v":0.9},
  {"name":"left_hip","x":380,"y":400,"v":0.9},
  {"name":"right_hip","x":420,"y":400,"v":0.9},
  {"name":"left_knee","x":370,"y":550,"v":0.9},
  {"name":"right_knee","x":430,"y":550,"v":0.9},
  {"name":"left_ankle","x":360,"y":700,"v":0.9},
  {"name":"right_ankle","x":440,"y":700,"v":0.9}
],"bbox":[300,50,500,750],"score":0.98}]'

# Reset the alert throttling by temporarily modifying the file
echo "Temporarily disabling alert throttling to ensure our test works..."
docker exec -it yolo_pose_api-alert-logic-1 /bin/bash -c "echo 'GLOBAL_ALERT_COOLDOWN = 0' > /tmp/override.py"

# Post to the alert-logic service
echo "Posting test alert to alert-logic service..."
RESPONSE=$(curl -s -X POST http://localhost:8012/alert \
    -F "camera_id=TEST_CAM" \
    -F "detection_type=poses" \
    -F "date_time=$DATETIME" \
    -F "image_source=$TEST_IMAGE" \
    -F "poses=$POSE_JSON")

echo "Response: $RESPONSE"

echo ""
echo "Step 2: Checking for alert images with the new naming format..."

# Wait a moment for processing
sleep 2

# Look for alert images
echo "Alert images in output_image directory:"
ls -la output_image/alert_* 2>/dev/null || echo "No alert images found"

echo ""
echo "==========================================================="
echo "  TEST COMPLETE"
echo "==========================================================="
