#!/usr/bin/env python3
# Test script to check weapon detection

import sys
import cv2
import os
from ultralytics import YOLO
from alert_logic.logic.detection_analysis import analyze_detections, draw_detection_boxes

def test_image(image_path, model_path='detector_detections/models/best.pt', conf_threshold=0.35):
    # Load model
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    print("Model loaded successfully.")
    
    # Load image
    print(f"Loading image from {image_path}...")
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image {image_path}")
        return False
    
    # Run detection
    results = model(img, conf=conf_threshold)
    
    # Format detections
    detections = []
    for i, (box, cls, conf) in enumerate(zip(results[0].boxes.xyxy.cpu().numpy(), 
                                    results[0].boxes.cls.cpu().numpy(),
                                    results[0].boxes.conf.cpu().numpy())):
        class_name = results[0].names[int(cls)]
        x1, y1, x2, y2 = box
        
        # Apply lower confidence threshold for weapon-related classes
        confidence = float(conf)
        is_weapon = any(weapon in class_name.lower() for weapon in ["gun", "pistol", "rifle", "knife", "weapon"])
        
        # Print detailed info for weapon detections
        if is_weapon:
            print(f"WEAPON DETECTED: {class_name} with confidence {confidence:.2f} at coordinates {[int(x1), int(y1), int(x2), int(y2)]}")
            
        detection = {
            "class_name": class_name,
            "confidence": confidence,
            "bbox": [int(x1), int(y1), int(x2), int(y2)]
        }
        detections.append(detection)

    # Analyze detections for alerts
    alert_indices, alert_types = analyze_detections(detections)
    
    # Print alert information
    if alert_indices:
        print(f"\nAlerts detected: {len(alert_indices)}")
        for idx in alert_indices:
            print(f"  - Alert {idx}: {detections[idx]['class_name']} with types {alert_types.get(idx, [])}")
    else:
        print("\nNo alerts detected")
    
    # Draw boxes on image
    if alert_indices:
        overlay = draw_detection_boxes(img, detections, alert_indices, alert_types)
        output_path = os.path.join(os.path.dirname(image_path), f"alert_overlay_{os.path.basename(image_path)}")
        cv2.imwrite(output_path, overlay)
        print(f"Alert overlay saved to {output_path}")
    
    return True

if __name__ == "__main__":
    # Use an image from the video
    import os
    import subprocess
    
    # Extract a frame from the video if not already done
    video_path = "videos/gun4_2.mp4"
    frame_path = "extracted_frame.jpg"
    
    if not os.path.exists(frame_path):
        # Extract frame around 500 (where weapons were detected)
        subprocess.call(["ffmpeg", "-i", video_path, "-vf", "select=eq(n\\,500)", "-vframes", "1", frame_path])
        print(f"Extracted frame from {video_path} to {frame_path}")
    
    # Test the frame
    test_image(frame_path)
