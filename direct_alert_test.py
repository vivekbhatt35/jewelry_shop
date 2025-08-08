#!/usr/bin/env python3
import requests
import json
import time
import argparse
from datetime import datetime

def test_alert_service(alert_service_url, camera_id="TEST_CAM_002"):
    """
    Send a mock detection directly to the alert service to test if it recognizes weapon alerts
    """
    # Create a timestamp
    timestamp = datetime.now().isoformat()
    
    # Mock weapon detection data
    mock_detections = [
        {
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.95,
            "bbox": [50, 50, 200, 400]
        },
        {
            "class_id": 1,
            "class_name": "person with weapon", 
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
            "image_source": "/app/output_image/source_test.jpg",  # This path should be accessible inside the container
            "image_overlay": "/app/output_image/overlay_test.jpg",  # This path should be accessible inside the container
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
    parser = argparse.ArgumentParser(description='Test alert service with mock weapon detection')
    parser.add_argument('--alert-url', default='http://localhost:8012/alert',
                        help='URL for the alert service')
    parser.add_argument('--camera-id', default='TEST_CAM_002',
                        help='Camera ID to use for the test')
    
    args = parser.parse_args()
    
    print(f"Testing alert service with mock weapon detection:")
    print(f"  Alert Service URL: {args.alert_url}")
    print(f"  Camera ID: {args.camera_id}")
    
    test_alert_service(args.alert_url, args.camera_id)

if __name__ == "__main__":
    main()
