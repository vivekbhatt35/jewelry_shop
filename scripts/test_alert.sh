#!/bin/bash

echo "==========================================================="
echo "  CREATING TEST ALERT"
echo "==========================================================="

echo "Step 1: Creating a test alert by directly posting to the alert-logic service..."

# Create a directory for test files if it doesn't exist
mkdir -p test_files

# Create a test pose JSON file with hands up pose
cat > test_files/test_pose.json << 'EOF'
[
  {
    "person_id": "test_person_123",
    "keypoints": [
      {"name": "nose", "x": 100, "y": 50, "v": 0.9},
      {"name": "left_eye", "x": 85, "y": 40, "v": 0.9},
      {"name": "right_eye", "x": 115, "y": 40, "v": 0.9},
      {"name": "left_ear", "x": 75, "y": 45, "v": 0.9},
      {"name": "right_ear", "x": 125, "y": 45, "v": 0.9},
      {"name": "left_shoulder", "x": 70, "y": 100, "v": 0.9},
      {"name": "right_shoulder", "x": 130, "y": 100, "v": 0.9},
      {"name": "left_elbow", "x": 60, "y": 70, "v": 0.9},
      {"name": "right_elbow", "x": 140, "y": 70, "v": 0.9},
      {"name": "left_wrist", "x": 50, "y": 40, "v": 0.9},
      {"name": "right_wrist", "x": 150, "y": 40, "v": 0.9},
      {"name": "left_hip", "x": 85, "y": 150, "v": 0.9},
      {"name": "right_hip", "x": 115, "y": 150, "v": 0.9},
      {"name": "left_knee", "x": 80, "y": 200, "v": 0.9},
      {"name": "right_knee", "x": 120, "y": 200, "v": 0.9},
      {"name": "left_ankle", "x": 75, "y": 250, "v": 0.9},
      {"name": "right_ankle", "x": 125, "y": 250, "v": 0.9}
    ],
    "bbox": [50, 30, 150, 250],
    "score": 0.95
  }
]
EOF

# Find an existing image to use for testing
TEST_IMAGE=$(find output_image -name "source_*.png" | head -1)
if [ -z "$TEST_IMAGE" ]; then
    echo "Error: No source image found for testing!"
    exit 1
fi

echo "Using test image: $TEST_IMAGE"

# Get the current datetime in the format the system expects
DATETIME=$(date '+%Y-%m-%d %H:%M:%S')

# Post to the alert-logic service
echo "Posting test alert with hands up pose..."
curl -X POST http://localhost:8012/alert \
    -F "camera_id=TEST_CAM" \
    -F "detection_type=poses" \
    -F "date_time=$DATETIME" \
    -F "image_source=$TEST_IMAGE" \
    -F "poses=@test_files/test_pose.json"

echo ""
echo "Step 2: Checking for alert images with the new naming format..."

# Wait a moment for processing
sleep 2

# Check for alert images
ls -la output_image/alert_*

echo ""
echo "==========================================================="
echo "  TEST COMPLETE"
echo "==========================================================="
