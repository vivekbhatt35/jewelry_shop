#!/usr/bin/env python3
import os
import json
import cv2
import uuid
from datetime import datetime
import pytz

# Set up mock data
output_dir = "/app/output_image"
os.makedirs(output_dir, exist_ok=True)

# Find an existing image to use for testing
test_images = [f for f in os.listdir(output_dir) if f.startswith("source_")]
if not test_images:
    print("Error: No source images found for testing!")
    exit(1)

test_image_path = os.path.join(output_dir, test_images[0])
print(f"Using test image: {test_image_path}")

# Get the current datetime in the format the system expects
india_tz = pytz.timezone('Asia/Kolkata')
dt_now = datetime.now(india_tz)
date_time = dt_now.strftime("%Y-%m-%d %H:%M:%S")

# Create a test alert manually
camera_id = "TEST_CAM"
person_id = "test_person_123"
alert_type = "Hands_Up"
formatted_dt = date_time.replace(':', '').replace(' ', '_').replace('-', '')

# Create the output filename with the improved naming format
file_name = f"alert_{camera_id}_{formatted_dt}_{person_id}_{alert_type}.jpg"
saved_overlay_path = os.path.join(output_dir, file_name)

# Load the source image
try:
    base_img = cv2.imread(test_image_path)
    if base_img is None or base_img.size == 0:
        print(f"Failed to load valid image from {test_image_path}")
        exit(1)
    
    print(f"Image loaded successfully, shape: {base_img.shape}")
except Exception as e:
    print(f"Error reading image: {str(e)}")
    exit(1)

# Draw a test bounding box to simulate a person detection
cv2.rectangle(base_img, (100, 50), (300, 500), (0, 0, 255), 3)
cv2.putText(base_img, "HANDS UP ALERT", (110, 40), 
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

# Save the test alert image
try:
    print(f"Saving alert image to {saved_overlay_path}")
    success = cv2.imwrite(saved_overlay_path, base_img)
    
    if not success or not os.path.exists(saved_overlay_path):
        print(f"Failed to save image to {saved_overlay_path}")
    else:
        # Verify the saved file
        if os.path.getsize(saved_overlay_path) > 0:
            print(f"Successfully saved alert image to {saved_overlay_path}")
        else:
            print(f"Alert image file is empty: {saved_overlay_path}")
except Exception as e:
    print(f"Error saving image: {str(e)}")
    exit(1)

print("Test completed successfully!")
