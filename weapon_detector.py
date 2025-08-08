#!/usr/bin/env python3
"""
This script processes video files for weapon detection and generates alerts.
It uses the YOLO model to detect weapons and applies the same alert logic used in the services.
"""
import os
import sys
import cv2
import argparse
import numpy as np
from datetime import datetime
import time
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("WeaponDetector")

try:
    # Try to import from the project
    from alert_logic.logic.detection_analysis import analyze_detections, draw_detection_boxes, ALERT_CATEGORIES
    from ultralytics import YOLO
except ImportError:
    logger.error("Failed to import required modules. Make sure you're running from the project root.")
    sys.exit(1)

# Define classes of interest with a focus on weapons
CLASSES_OF_INTEREST = [
    "person", "knife", "scissors", "gun", "pistol", "rifle", "weapon", "person with weapon", 
    "mask", "helmet", "backpack", "suspicious behavior"
]

# Set lower confidence threshold for weapon detection
WEAPON_CLASSES = ["weapon"]  # Updated for new class structure
DEFAULT_CONF_THRESHOLD = 0.35
WEAPON_CONF_THRESHOLD = 0.25  # Lower threshold for weapons

def format_detections(results):
    """Format YOLO results into the same format used by the alert service"""
    detections = []
    for i, (box, cls, conf) in enumerate(zip(results[0].boxes.xyxy.cpu().numpy(), 
                                    results[0].boxes.cls.cpu().numpy(),
                                    results[0].boxes.conf.cpu().numpy())):
        class_name = results[0].names[int(cls)]
        x1, y1, x2, y2 = box
        
        # Apply class-specific confidence threshold
        confidence = float(conf)
        is_weapon = any(weapon.lower() in class_name.lower() for weapon in WEAPON_CLASSES)
        
        # Log all weapon detections, even if below threshold
        if is_weapon:
            log_method = logger.info if confidence >= WEAPON_CONF_THRESHOLD else logger.debug
            log_method(f"WEAPON DETECTED: {class_name} with confidence {confidence:.2f}")
            
        # Only add detections that meet the threshold
        threshold = WEAPON_CONF_THRESHOLD if is_weapon else DEFAULT_CONF_THRESHOLD
        if confidence >= threshold:
            detection = {
                "class_name": class_name,
                "confidence": confidence,
                "bbox": [int(x1), int(y1), int(x2), int(y2)]
            }
            detections.append(detection)
    
    return detections

def process_video(input_video, output_video, model_path, alert_output_dir=None):
    """Process a video file for weapon detection"""
    logger.info(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    logger.info("Model loaded successfully.")
    
    logger.info(f"Opening video: {input_video}")
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        logger.error(f"Error: Could not open video {input_video}")
        return False
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    logger.info(f"Video properties: {width}x{height}, {fps} fps, {total_frames} frames")
    
    # Set up output video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    # Create alert output directory if specified
    if alert_output_dir:
        os.makedirs(alert_output_dir, exist_ok=True)
    
    frame_count = 0
    start_time = time.time()
    alert_counters = {alert_type: 0 for alert_type in ALERT_CATEGORIES.keys()}
    alert_counters["Total"] = 0
    alerts_triggered = []
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run detection with normal confidence first
            results = model(frame, conf=DEFAULT_CONF_THRESHOLD)
            detections = format_detections(results)
            
            # Analyze for alerts
            alert_indices, alert_types = analyze_detections(detections)
            
            # Process alerts
            if alert_indices:
                alert_counters["Total"] += 1
                for idx in alert_indices:
                    if idx < len(detections):
                        for alert_type in alert_types.get(idx, []):
                            alert_counters[alert_type] = alert_counters.get(alert_type, 0) + 1
                            
                        # Save weapon alerts as separate images if directory specified
                        detection = detections[idx]
                        is_weapon_alert = any(a == "Weapon" for a in alert_types.get(idx, []))
                        if is_weapon_alert and alert_output_dir:
                            # Save the frame with the weapon detection
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            frame_filename = f"weapon_{timestamp}_frame{frame_count}.jpg"
                            frame_path = os.path.join(alert_output_dir, frame_filename)
                            
                            # Draw box around just this detection for the alert image
                            alert_frame = frame.copy()
                            x1, y1, x2, y2 = detection["bbox"]
                            cv2.rectangle(alert_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                            cv2.putText(alert_frame, f"{detection['class_name']} {detection['confidence']:.2f}", 
                                      (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                            
                            cv2.imwrite(frame_path, alert_frame)
                            logger.info(f"Saved weapon alert frame to {frame_path}")
                            
                            # Add to alerts list
                            alerts_triggered.append({
                                "frame": frame_count,
                                "time_in_video": frame_count / fps,
                                "class": detection["class_name"],
                                "confidence": detection["confidence"],
                                "bbox": detection["bbox"],
                                "image_path": frame_path
                            })
            
            # Draw all detections on the frame
            overlay_frame = draw_detection_boxes(frame, detections, alert_indices, alert_types)
            
            # Add frame information
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_in_video = frame_count / fps
            cv2.putText(overlay_frame, f"Frame: {frame_count} | Time: {time_in_video:.2f}s", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
            # Add alert counter information
            alert_text = " | ".join([f"{k}: {v}" for k, v in alert_counters.items() if v > 0])
            if alert_text:
                cv2.putText(overlay_frame, alert_text, 
                          (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Write frame to output video
            out.write(overlay_frame)
            
            # Progress reporting
            frame_count += 1
            if frame_count % 50 == 0:
                logger.info(f"Processed {frame_count}/{total_frames} frames...")
            
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
    finally:
        cap.release()
        out.release()
    
    elapsed_time = time.time() - start_time
    logger.info(f"Processing completed:")
    logger.info(f"- Processed {frame_count} frames in {elapsed_time:.2f} seconds ({frame_count/elapsed_time:.2f} fps)")
    logger.info(f"- Output video saved to: {output_video}")
    logger.info("Alert counts:")
    for alert_type, count in alert_counters.items():
        if count > 0:
            logger.info(f"- {alert_type}: {count}")
    
    # Save alerts to JSON file if there are any weapon alerts and output directory is specified
    if alerts_triggered and alert_output_dir:
        alert_json_path = os.path.join(alert_output_dir, "weapon_alerts.json")
        with open(alert_json_path, 'w') as f:
            json.dump(alerts_triggered, f, indent=2)
        logger.info(f"Saved {len(alerts_triggered)} weapon alerts to {alert_json_path}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process video for weapon detection")
    parser.add_argument("input", help="Input video file path")
    parser.add_argument("output", help="Output video file path")
    parser.add_argument("--model", "-m", default="detector_detections/models/best.pt", 
                        help="Path to YOLO model file")
    parser.add_argument("--alert-dir", "-a", help="Directory to save alert frames")
    parser.add_argument("--conf", "-c", type=float, default=DEFAULT_CONF_THRESHOLD,
                        help=f"Confidence threshold (default: {DEFAULT_CONF_THRESHOLD})")
    parser.add_argument("--weapon-conf", "-w", type=float, default=WEAPON_CONF_THRESHOLD,
                        help=f"Weapon confidence threshold (default: {WEAPON_CONF_THRESHOLD})")
    
    args = parser.parse_args()
    
    # Update thresholds based on arguments
    DEFAULT_CONF_THRESHOLD = args.conf
    WEAPON_CONF_THRESHOLD = args.weapon_conf
    
    logger.info(f"Default confidence threshold: {DEFAULT_CONF_THRESHOLD}")
    logger.info(f"Weapon confidence threshold: {WEAPON_CONF_THRESHOLD}")
    
    success = process_video(args.input, args.output, args.model, args.alert_dir)
    sys.exit(0 if success else 1)
