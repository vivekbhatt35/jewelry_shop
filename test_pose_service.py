#!/usr/bin/env python3
import os
import requests
import argparse
import cv2
from PIL import Image
import io

def test_pose_service(image_path, service_url="http://localhost:8011/pose/image", camera_id="TEST_CAM", output_image=1):
    """
    Test the pose detection service by sending an image and displaying the results
    
    Args:
        image_path: Path to the image file to send
        service_url: URL of the pose detection service
        camera_id: Camera ID to use in the request
        output_image: Whether to request an overlay image (1) or not (0)
    """
    print(f"Testing pose detection service at {service_url} with image {image_path}")
    
    # Make sure the image exists
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    # Open the image file
    with open(image_path, "rb") as f:
        img_data = f.read()
        
    # Create the form data for the request
    files = {"file": (os.path.basename(image_path), img_data)}
    data = {
        "camera_id": camera_id,
        "output_image": str(output_image)
    }
    
    try:
        # Send the request to the pose detection service
        print(f"Sending request to {service_url}...")
        response = requests.post(service_url, files=files, data=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            print("\nResponse from pose detection service:")
            print(f"Camera ID: {result.get('camera_id')}")
            print(f"Timestamp: {result.get('timestamp')}")
            print(f"Number of poses detected: {len(result.get('poses', []))}")
            
            # Print the first pose if any were detected
            poses = result.get('poses', [])
            if poses:
                print("\nFirst pose detected (first 10 keypoints):")
                # Print the first 10 keypoints to keep output manageable
                first_pose = poses[0]
                for i in range(0, min(30, len(first_pose)), 3):
                    x, y, v = first_pose[i], first_pose[i+1], first_pose[i+2]
                    print(f"Keypoint {i//3}: x={x}, y={y}, v={v}")
            
            # Check for overlay image
            overlay_path = result.get('overlay_image_path')
            source_path = result.get('source_image')
            
            if overlay_path:
                print(f"\nOverlay image saved to: {overlay_path}")
                
                # Try to display the overlay image if possible
                if os.path.exists(overlay_path):
                    img = cv2.imread(overlay_path)
                    if img is not None:
                        cv2.imshow("Pose Detection Result", img)
                        cv2.waitKey(0)
                        cv2.destroyAllWindows()
                    else:
                        print(f"Warning: Could not read overlay image from {overlay_path}")
                else:
                    print(f"Warning: Overlay image not found at {overlay_path}")
            
            # Check for alert status
            alert_status = result.get('alert_status', {})
            if alert_status:
                print("\nAlert status:")
                print(f"Type of alert: {alert_status.get('type_of_alert', 'None')}")
                if 'error' in alert_status:
                    print(f"Alert error: {alert_status.get('error')}")
            
            return result
        else:
            print(f"Error: Request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error sending request: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test pose detection service')
    parser.add_argument('image_path', help='Path to the image file to send')
    parser.add_argument('--url', default="http://localhost:8011/pose/image", 
                        help='URL of the pose detection service')
    parser.add_argument('--camera', default="TEST_CAM", help='Camera ID to use in the request')
    parser.add_argument('--output', type=int, default=1, help='Whether to request an overlay image (1) or not (0)')
    
    args = parser.parse_args()
    test_pose_service(args.image_path, args.url, args.camera, args.output)
