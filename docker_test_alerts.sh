#!/bin/bash

# Make this script executable with:
# chmod +x docker_test_alerts.sh

echo "Running weapon alert test within Docker containers"

# 1. Create test images and test the detection analysis directly
echo "Creating test images and testing alert logic..."
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_SOURCE_IMG="/app/output_image/source_test_${TIMESTAMP}.jpg"
TEST_OVERLAY_IMG="/app/output_image/overlay_test_${TIMESTAMP}.jpg"

# Run Python script inside the alert-logic container to test the alert logic directly
docker exec yolo_pose_api-alert-logic-1 python -c "
import json
import os
import cv2
import numpy as np
from datetime import datetime

# Create test images
height, width = 480, 640
test_img = np.ones((height, width, 3), dtype=np.uint8) * 200  # Light gray
cv2.putText(test_img, 'Test Person with Weapon', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
cv2.rectangle(test_img, (50, 50), (200, 400), (255, 0, 0), 2)  # Person - blue
cv2.rectangle(test_img, (250, 150), (400, 350), (0, 0, 255), 2)  # Weapon - red

# Save both source and overlay images
test_source_path = '$TEST_SOURCE_IMG'
test_overlay_path = '$TEST_OVERLAY_IMG'
cv2.imwrite(test_source_path, test_img)
cv2.imwrite(test_overlay_path, test_img)
print(f'Created test images: {test_source_path} and {test_overlay_path}')

# Create test detections inline instead of from file
detections = [
  {
    'class_id': 0,
    'class_name': 'person',
    'confidence': 0.95,
    'bbox': [50, 50, 200, 400]
  },
  {
    'class_id': 1,
    'class_name': 'person with weapon',
    'confidence': 0.88,
    'bbox': [250, 150, 400, 350]
  }
]

# Import modules
from logic.detection_analysis import analyze_detections, ALERT_CATEGORIES

# Check if 'person with weapon' is in the weapon category
person_with_weapon_in_categories = any('person with weapon' in classes for classes in ALERT_CATEGORIES.values())
print(f'ALERT_CATEGORIES: {ALERT_CATEGORIES}')
print(f'Is \"person with weapon\" in alert categories: {person_with_weapon_in_categories}')

# Run the detection analysis
alert_indices, alert_types = analyze_detections(detections)
print(f'Alert analysis results:')
print(f'Alert indices: {alert_indices}')
print(f'Alert types: {alert_types}')

if len(alert_indices) > 0 and any('Weapon' in alert_types.get(idx, []) for idx in alert_indices):
    print('SUCCESS: Weapon alert detected!')
else:
    print('FAIL: No weapon alert detected!')
"

# 2. Test the alert API using Python's requests module (since curl is not installed)
echo "Testing direct alert endpoint using Python requests..."
docker exec yolo_pose_api-alert-logic-1 python -c "
import requests
import json
from datetime import datetime

# Test data
camera_id = 'TEST_CAM_001'
detection_type = 'objects'
date_time = datetime.now().isoformat()
image_source = '$TEST_SOURCE_IMG'
image_overlay = '$TEST_OVERLAY_IMG'

# Create test detections - putting the person and weapon bounding boxes closer to each other
detections = [
  {
    'class_id': 0,
    'class_name': 'person',
    'confidence': 0.95,
    'bbox': [150, 150, 250, 350]
  },
  {
    'class_id': 1,
    'class_name': 'person with weapon',
    'confidence': 0.88,
    'bbox': [200, 150, 300, 350]
  }
]

# Make API request
try:
    response = requests.post(
        'http://localhost:8012/alert',
        data={
            'camera_id': camera_id,
            'detection_type': detection_type,
            'date_time': date_time,
            'image_source': image_source, 
            'image_overlay': image_overlay,
            'detections': json.dumps(detections)
        }
    )
    print(f'Response status: {response.status_code}')
    print(f'Response body: {response.text}')
    if response.status_code == 200:
        print('SUCCESS: Alert API call successful')
    else:
        print('FAIL: Alert API call failed')
except Exception as e:
    print(f'ERROR: {str(e)}')
"

echo -e "\nTest completed!"
