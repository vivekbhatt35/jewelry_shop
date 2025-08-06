#!/usr/bin/env python3
"""
Test script for person tracking module.
This script demonstrates the functionality of the person tracking module
without needing to run the full camera manager application.
"""
import cv2
import numpy as np
import time
import os
import sys
import json
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from camera_manager.person_tracker import PersonTracker

def main():
    parser = argparse.ArgumentParser(description='Test person tracking functionality')
    parser.add_argument('--video', type=str, help='Path to video file for testing')
    parser.add_argument('--output', type=str, default='tracking_output.mp4', 
                        help='Path to output video file')
    parser.add_argument('--interval', type=int, default=60, 
                        help='Alert interval in seconds')
    parser.add_argument('--distance', type=int, default=100, 
                        help='Max distance threshold for tracking')
    parser.add_argument('--iou', type=float, default=0.3, 
                        help='Minimum IOU threshold for tracking')
    args = parser.parse_args()
    
    # Check if video path is provided
    if not args.video:
        print("Error: Please provide a path to a video file with --video")
        return
    
    # Initialize tracker
    tracker = PersonTracker(
        max_distance_threshold=args.distance,
        min_iou_threshold=args.iou,
        use_spatial=True,
        use_appearance=False,
        person_memory=120
    )
    tracker.alert_interval = args.interval
    
    # Open video
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: Could not open video file {args.video}")
        return
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Create output video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    
    frame_count = 0
    
    # Mock alert detection
    def generate_mock_detections(frame):
        """Generate mock detections for testing"""
        # For simplicity, just detect people as bounding boxes
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        face_rects = faces.detectMultiScale(gray, 1.3, 5)
        
        detections = []
        
        # Add person detections based on face detection (for simple testing)
        for (x, y, w, h) in face_rects:
            # Make person bounding box larger than the face
            person_width = w * 3
            person_height = h * 5
            person_x = max(0, x - w)
            person_y = max(0, y - h)
            
            # Ensure box doesn't go outside frame
            person_width = min(width - person_x, person_width)
            person_height = min(height - person_y, person_height)
            
            detections.append({
                "class_name": "person",
                "bbox": [person_x, person_y, person_x + person_width, person_y + person_height],
                "confidence": 0.9
            })
            
        return detections
    
    # Mock alert response
    def generate_mock_alert(detections, frame_count):
        """Generate mock alerts for testing"""
        if not detections:
            return {"type_of_alert": "No_Alert"}
        
        # Every 30 frames, generate a hands up alert for the first person
        if frame_count % 30 == 0 and detections:
            return {
                "type_of_alert": "Hands_Up",
                "Detection_type": "poses",
                "Image_bb": [detections[0]["bbox"]]
            }
        
        # Every 50 frames, generate a weapon alert for the first person
        if frame_count % 50 == 0 and detections:
            return {
                "type_of_alert": "Weapon",
                "Detection_type": "objects",
                "Image_bb": [detections[0]["bbox"]]
            }
            
        return {"type_of_alert": "No_Alert"}
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # Generate mock detections and alerts
            detections = generate_mock_detections(frame)
            
            # Process detections through tracker
            person_map = tracker.update(detections)
            
            # Generate mock alert
            mock_alert = generate_mock_alert(detections, frame_count)
            
            # Apply alert filtering
            filtered_alert = tracker.filter_alerts(mock_alert, person_map)
            
            # Visualize tracking
            for i, detection in enumerate(detections):
                bbox = detection["bbox"]
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                
                # Default color is green for regular detection
                color = (0, 255, 0)
                thickness = 2
                
                # If this detection is mapped to a tracked person, show the ID
                if i in person_map:
                    person_id = person_map[i]
                    person = tracker.people[person_id]
                    
                    # Check if this person has any recent alerts (show in red)
                    recent_alert = False
                    for alert_type, last_time in person.last_alert_time.items():
                        if last_time > 0 and time.time() - last_time < tracker.alert_interval:
                            recent_alert = True
                            break
                    
                    if recent_alert:
                        # Red for persons with recent alerts (throttled)
                        color = (0, 0, 255)
                        thickness = 3
                    
                    # Draw ID on the bounding box
                    short_id = person_id[-6:]  # Last 6 chars of UUID
                    cv2.putText(frame, f"ID: {short_id}", (x1, y1-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    # Draw alert status
                    alert_text = []
                    for alert_type, last_time in person.last_alert_time.items():
                        if last_time > 0:
                            seconds_ago = int(time.time() - last_time)
                            if seconds_ago < tracker.alert_interval:
                                alert_text.append(f"{alert_type}: {seconds_ago}s ago")
                    
                    if alert_text:
                        for i, text in enumerate(alert_text):
                            cv2.putText(frame, text, (x1, y1+20+(i*20)), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                
                # Draw the bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Show alert status on the frame
            if mock_alert["type_of_alert"] != "No_Alert":
                cv2.putText(frame, f"Original Alert: {mock_alert['type_of_alert']}", 
                            (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            if filtered_alert["type_of_alert"] != "No_Alert":
                cv2.putText(frame, f"Filtered Alert: {filtered_alert['type_of_alert']}", 
                            (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                if mock_alert["type_of_alert"] != "No_Alert":
                    cv2.putText(frame, "Alert Suppressed!", 
                                (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Show tracking stats
            cv2.putText(frame, f"Tracked persons: {len(tracker.people)}", 
                        (50, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Alert interval: {args.interval}s", 
                        (50, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Write frame to output video
            out.write(frame)
            
            # Display frame
            cv2.imshow('Tracking Test', frame)
            
            # Break on ESC key
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        print(f"Output video saved to {args.output}")

if __name__ == "__main__":
    main()
