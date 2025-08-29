#!/bin/bash
# Test script for detector-detections service

# Configuration
DETECTOR_URL="http://localhost:8013"
TEST_IMAGE="test_image.jpg"  # Put a test image in the same directory
CAMERA_ID="TEST_CAM_001"

echo "Testing detector-detections service with new class model"
echo "======================================================"

# Check if service is running
echo "Checking if detector service is running..."
if ! curl -s "$DETECTOR_URL/health" > /dev/null; then
    echo "ERROR: Detector service is not running. Start it with: docker-compose up detector-detections"
    exit 1
fi

# Check health and model info
echo "Checking detector health and model information..."
HEALTH_INFO=$(curl -s "$DETECTOR_URL/health")
echo $HEALTH_INFO | grep -q "\"model_loaded\": true"
if [ $? -ne 0 ]; then
    echo "WARNING: Model doesn't appear to be loaded properly."
    echo "Health info: $HEALTH_INFO"
    echo ""
    echo "Continuing test anyway..."
else
    echo "Model loaded successfully!"
    echo "Health info: $HEALTH_INFO"
    echo ""
fi

# Check if test image exists
if [ ! -f "$TEST_IMAGE" ]; then
    echo "ERROR: Test image '$TEST_IMAGE' not found."
    echo "Please place a test image named '$TEST_IMAGE' in the current directory."
    exit 1
fi

# Test direct image upload endpoint
echo "Testing /detect/image endpoint..."
curl -s -X POST -F "file=@$TEST_IMAGE" -F "camera_id=$CAMERA_ID" -F "output_image=1" "$DETECTOR_URL/detect/image" > detect_result.json
echo "Results saved to detect_result.json"

# Test camera_frame endpoint
echo "Testing /camera_frame endpoint..."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
curl -s -X POST -F "frame=@$TEST_IMAGE" -F "camera_id=$CAMERA_ID" -F "timestamp=$TIMESTAMP" "$DETECTOR_URL/camera_frame" > camera_result.json
echo "Results saved to camera_result.json"

# Display results summary
echo ""
echo "Detection Results Summary:"
echo "========================="
echo "Direct detection found: $(grep -o "class_name" detect_result.json | wc -l) objects"
echo "Camera frame detection found: $(grep -o "class_name" camera_result.json | wc -l) objects"
echo ""
echo "Check the output_image directory for generated images."
echo "You can view the full JSON responses in detect_result.json and camera_result.json files."
