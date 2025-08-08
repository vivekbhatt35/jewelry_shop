#!/bin/bash

# This script uses Ultralytics YOLO to process a video file and create an overlay output

if [ $# -lt 2 ]; then
    echo "Usage: $0 <input_video> <output_video> [model_path] [conf_threshold]"
    echo "Example: $0 videos/video1.mp4 output_video.mp4"
    exit 1
fi

INPUT_VIDEO="$1"
OUTPUT_VIDEO="$2"
MODEL_PATH="${3:-detector_detections/models/best.pt}"
CONF_THRESHOLD="${4:-0.35}"

if [ ! -f "$INPUT_VIDEO" ]; then
    echo "Error: Input video file not found: $INPUT_VIDEO"
    exit 1
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found: $MODEL_PATH"
    exit 1
fi

echo "Creating Python script..."

cat > run_video_detection.py << 'EOF'
import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import time
from alert_logic.logic.detection_analysis import analyze_detections, draw_detection_boxes, ALERT_CATEGORIES

def format_detections(results):
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
    return detections

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_video_detection.py <input_video> <output_video> [model_path] [conf_threshold]")
        return False
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    model_path = sys.argv[3] if len(sys.argv) > 3 else 'detector_detections/models/best.pt'
    conf_threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35
    weapon_conf_threshold = conf_threshold * 0.8  # Use lower threshold for weapons
    
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    print("Model loaded successfully.")
    
    print(f"Opening video: {input_video}")
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print(f"Error: Could not open video {input_video}")
        return False
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video properties: {width}x{height}, {fps} fps, {total_frames} frames")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    frame_count = 0
    start_time = time.time()
    alert_counters = {alert_type: 0 for alert_type in ALERT_CATEGORIES.keys()}
    alert_counters["Total"] = 0
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run detection with normal confidence
            results = model(frame, conf=conf_threshold)
            detections = format_detections(results)
            
            # For frames where no weapons are detected, try with lower confidence for weapon detection
            if not any("weapon" in d["class_name"].lower() or 
                      "gun" in d["class_name"].lower() or 
                      "knife" in d["class_name"].lower() for d in detections):
                weapon_results = model(frame, conf=weapon_conf_threshold)
                weapon_detections = format_detections(weapon_results)
                # If we found weapon detections with lower threshold, use those instead
                for detection in weapon_detections:
                    if any(weapon in detection["class_name"].lower() for weapon in ["gun", "pistol", "rifle", "knife", "weapon"]):
                        if detection not in detections:
                            print(f"Added weapon detection with lower threshold: {detection['class_name']}")
                            detections.append(detection)
            
            alert_indices, alert_types = analyze_detections(detections)
            
            if alert_indices:
                alert_counters["Total"] += 1
                for idx in alert_indices:
                    for alert_type in alert_types.get(idx, []):
                        alert_counters[alert_type] = alert_counters.get(alert_type, 0) + 1
            
            overlay_frame = draw_detection_boxes(frame, detections, alert_indices, alert_types)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(overlay_frame, f"Frame: {frame_count} | Time: {timestamp}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            alert_text = " | ".join([f"{k}: {v}" for k, v in alert_counters.items() if v > 0])
            if alert_text:
                cv2.putText(overlay_frame, alert_text, 
                          (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            out.write(overlay_frame)
            
            frame_count += 1
            if frame_count % 50 == 0:
                print(f"Processed {frame_count}/{total_frames} frames...")
            
    except Exception as e:
        print(f"\nError during processing: {str(e)}")
    finally:
        cap.release()
        out.release()
    
    elapsed_time = time.time() - start_time
    print(f"\nProcessing completed:")
    print(f"- Processed {frame_count} frames in {elapsed_time:.2f} seconds ({frame_count/elapsed_time:.2f} fps)")
    print(f"- Output saved to: {output_video}")
    print("Alert counts:")
    for alert_type, count in alert_counters.items():
        if count > 0:
            print(f"- {alert_type}: {count}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

echo "Running detection on video..."
python run_video_detection.py "$INPUT_VIDEO" "$OUTPUT_VIDEO" "$MODEL_PATH" "$CONF_THRESHOLD"

exit $?
