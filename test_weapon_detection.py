#!/usr/bin/env python3
import requests
import json
import os
import time
import base64
import argparse
from datetime import datetime
import cv2
import numpy as np

def create_test_image_with_label(label, width=640, height=480):
    """
    Create a test image with a text label that would simulate a weapon detection
    """
    # Create a blank image
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img.fill(200)  # Light gray background
    
    # Add text in the center
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = f"Test Image: {label}"
    text_size = cv2.getTextSize(text, font, 1, 2)[0]
    
    # Calculate text position to center it
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    
    # Add text to image
    cv2.putText(img, text, (text_x, text_y), font, 1, (0, 0, 0), 2)
    
    # Draw a box representing the detection
    cv2.rectangle(img, (width//4, height//4), (width*3//4, height*3//4), (0, 0, 255), 2)
    
    return img

def create_test_image_with_person_and_weapon(width=640, height=480):
    """
    Create a test image with a person and a weapon nearby
    """
    # Create a blank image
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img.fill(200)  # Light gray background
    
    # Draw a "person" rectangle in blue
    person_x1, person_y1 = width//4, height//4
    person_x2, person_y2 = width//2, height*3//4
    cv2.rectangle(img, (person_x1, person_y1), (person_x2, person_y2), (255, 0, 0), 2)
    cv2.putText(img, "Person", (person_x1, person_y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Draw a "weapon" rectangle in red, close to the person
    weapon_x1, weapon_y1 = width//2 + 20, height//2
    weapon_x2, weapon_y2 = width*3//4, height*3//4
    cv2.rectangle(img, (weapon_x1, weapon_y1), (weapon_x2, weapon_y2), (0, 0, 255), 2)
    cv2.putText(img, "Weapon", (weapon_x1, weapon_y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    return img

def inject_mock_detection(image_path, detection_service_url, camera_id):
    """
    Send a test image to the detection service with a simulated weapon detection
    """
    # Read the image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Prepare the request
    files = {
        'file': (os.path.basename(image_path), image_data),
    }
    
    data = {
        'output_image': '1',
        'camera_id': camera_id
    }
    
    # Send the request to the detection service
    try:
        response = requests.post(
            detection_service_url,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            print(f"Successfully sent test image to detection service")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.json()
        else:
            print(f"Error: Detection service returned {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception when sending image to detection service: {str(e)}")
        return None

def mock_detection(detection_service_url, alert_service_url, camera_id):
    """
    Create a mock detection and send it directly to the alert service
    """
    # Create a timestamp
    timestamp = datetime.now().isoformat()
    
    # Create test image
    temp_image_path = "test_weapon_detection.jpg"
    test_image = create_test_image_with_person_and_weapon()
    cv2.imwrite(temp_image_path, test_image)
    
    # Get the path to the saved image
    absolute_path = os.path.abspath(temp_image_path)
    print(f"Created test image at {absolute_path}")
    
    # First approach: Send image to detection service and let it forward to alert service
    print("Approach 1: Sending image to detection service")
    detection_result = inject_mock_detection(
        temp_image_path, 
        detection_service_url, 
        camera_id
    )
    
    # Second approach: Construct a mock detection manually and use Docker volume path
    print("\nApproach 2: Constructing mock detection for alert service")
    # Copy image to shared Docker volume path
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    docker_image_name = f"source_test_weapon_{timestamp_str}.jpg"
    docker_image_path = f"/Users/vivek/yolo_pose_api/output_image/{docker_image_name}" 
    docker_volume_path = f"/app/output_image/{docker_image_name}"
    
    # Copy the image to the shared Docker volume path
    cv2.imwrite(docker_image_path, test_image)
    print(f"Copied test image to shared Docker volume at {docker_image_path}")
    
    # Mock a weapon detection
    mock_detections = [
        {
            "class_id": 1,
            "class_name": "person",
            "confidence": 0.95,
            "bbox": [50, 50, 200, 400]
        },
        {
            "class_id": 2,
            "class_name": "person with weapon",  # Use the new class we added
            "confidence": 0.85,
            "bbox": [250, 150, 400, 350]
        }
    ]
    
    # Send it directly to the alert service
    try:
        alert_data = {
            "camera_id": camera_id,
            "detection_type": "objects",
            "date_time": timestamp,
            "image_source": docker_volume_path,  # Use Docker volume path
            "image_overlay": docker_volume_path,  # Just use the same image for simplicity
            "detections": json.dumps(mock_detections)
        }
        
        print(f"Sending alert data: {json.dumps(alert_data, indent=2)}")
        
        alert_response = requests.post(
            alert_service_url,
            data=alert_data
        )
        
        if alert_response.status_code == 200:
            print("Successfully sent mock detection to alert service")
            print(f"Response: {json.dumps(alert_response.json(), indent=2)}")
        else:
            print(f"Error: Alert service returned {alert_response.status_code}")
            print(f"Response: {alert_response.text}")
    except Exception as e:
        print(f"Exception when sending mock detection to alert service: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Test weapon detection and alert generation')
    parser.add_argument('--detection-url', default='http://localhost:8013/detect/image',
                        help='URL for the detection service')
    parser.add_argument('--alert-url', default='http://localhost:8012/alert',
                        help='URL for the alert service')
    parser.add_argument('--camera-id', default='TEST_CAM_001',
                        help='Camera ID to use for the test')
    
    args = parser.parse_args()
    
    print(f"Testing weapon detection with:")
    print(f"  Detection Service URL: {args.detection_url}")
    print(f"  Alert Service URL: {args.alert_url}")
    print(f"  Camera ID: {args.camera_id}")
    
    mock_detection(args.detection_url, args.alert_url, args.camera_id)
    
    # Clean up the test image
    if os.path.exists("test_weapon_detection.jpg"):
        os.remove("test_weapon_detection.jpg")
        print("Cleaned up test image")

if __name__ == "__main__":
    main()
