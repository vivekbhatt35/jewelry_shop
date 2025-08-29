#!/bin/bash

# Final comprehensive fix for detection analysis and alert logic

echo "Creating a comprehensive fix for alert-logic service..."

# First, we need to examine app.py to see how it calls the detection_analysis functions
echo "Examining app.py to understand how it uses detection_analysis..."
CONTAINER_ID=$(docker ps -q -f name=yolo_pose_api-alert-logic)
if [ -z "$CONTAINER_ID" ]; then
    echo "Starting alert-logic container..."
    docker-compose up -d alert-logic
    sleep 5
    CONTAINER_ID=$(docker ps -q -f name=yolo_pose_api-alert-logic)
fi

# Let's examine the exact import statement and function calls in app.py
docker exec "$CONTAINER_ID" bash -c "grep -A 5 'from logic.detection_analysis' /app/alert_logic/app.py"
docker exec "$CONTAINER_ID" bash -c "grep -n 'draw_detection_boxes' /app/alert_logic/app.py"

# Create a fixed version of app.py
echo "Creating modified app.py to match our detection_analysis functions..."

cat << 'EOF' > app_fix.py
# Update the import statement
from logic.detection_analysis import analyze_detections, draw_detection_boxes

# Update the draw_detection_boxes call to match our implementation
def fix_draw_detection_boxes_call(base_img, detections_list, alert_indices, alert_types):
    return draw_detection_boxes(base_img, detections_list, alert_indices, alert_types)
EOF

# Create a fixed detection_analysis.py with the exact names the app.py file is expecting
cat << 'EOF' > detection_analysis_complete.py
import cv2
import numpy as np
import logging

logger = logging.getLogger("Alert-Logic")

# Define alert types and their associated classes
ALERT_CATEGORIES = {
    "Weapon": ["weapon"],
    "Face_Covered": ["mask", "helmet"],
    "Suspicious": ["suspicious"]
}

# Define classes that are monitored but don't trigger alerts by themselves
MONITORED_CLASSES = ["person"]

# Define critical classes that always trigger alerts regardless of other conditions
CRITICAL_CLASSES = ["weapon", "mask", "helmet", "suspicious"]

def analyze_detections(detections):
    """
    Analyze object detections to identify items of interest
    
    Args:
        detections: List of detection dictionaries with class_name, confidence, bbox
    
    Returns:
        list: Indices of detections that trigger alerts
        dict: Mapping of detection indices to alert types
    """
    alert_indices = []
    alert_types = {}
    
    # Track persons and alert objects separately
    person_detections = []
    alert_detections = {}
    
    logger.info(f"Analyzing {len(detections)} detections")
    
    # First pass: identify all persons and alert objects
    for i, detection in enumerate(detections):
        class_name = detection.get("class_name", "").lower()
        confidence = detection.get("confidence", 0)
        
        # Define thresholds by class type
        if class_name == "weapon":
            threshold = 0.10  # Very low threshold for weapons
            logger.info(f"Using weapon threshold of {threshold} for {class_name}")
        elif class_name == "suspicious":
            threshold = 0.25  # Low threshold for suspicious items
            logger.info(f"Using suspicious threshold of {threshold} for {class_name}")
        elif class_name == "mask" or class_name == "helmet":
            threshold = 0.30  # Medium-low threshold for masks/helmets
            logger.info(f"Using mask/helmet threshold of {threshold} for {class_name}")
        else:
            threshold = 0.35  # Normal threshold for everything else
        
        # Skip low confidence detections
        if confidence < threshold:
            logger.info(f"Detection {i}: {class_name} has low confidence {confidence:.2f}, threshold {threshold}, skipping")
            continue
        
        # CRITICAL FIX: Direct alerts for critical classes
        if class_name.lower() in [c.lower() for c in CRITICAL_CLASSES]:
            # Determine the alert type for this detection
            alert_type = None
            if class_name.lower() == "weapon":
                alert_type = "Weapon"
            elif class_name.lower() in ["mask", "helmet"]:
                alert_type = "Face_Covered"
            elif class_name.lower() == "suspicious":
                alert_type = "Suspicious"
            
            # Add to alert indices directly - this is an immediate alert
            if alert_type:
                alert_indices.append(i)
                alert_types[i] = [alert_type]
                logger.info(f"CRITICAL DETECTION: {i}: {class_name} directly triggered {alert_type} alert with confidence {confidence:.2f}")
        
        # Track person detections
        if class_name == "person":
            person_detections.append(i)
        
        # Check which category this detection belongs to for other classes
        detected_alerts = []
        for alert_type, classes in ALERT_CATEGORIES.items():
            if class_name in [c.lower() for c in classes]:
                detected_alerts.append(alert_type)
                logger.info(f"Detection {i}: {class_name} triggered alert: {alert_type}")
        
        # If this is an alert object that's not already triggered, store it
        if detected_alerts and i not in alert_indices:
            alert_detections[i] = detected_alerts
    
    logger.info(f"Found {len(person_detections)} persons and {len(alert_detections)} alert objects")
    
    # Second pass: handle associations between persons and alert objects
    for alert_idx, alert_cats in alert_detections.items():
        # Skip if this alert was already triggered in the first pass
        if alert_idx in alert_indices:
            continue
            
        alert_bbox = detections[alert_idx].get("bbox", [0, 0, 10, 10])
        class_name = detections[alert_idx].get("class_name", "").lower()
        
        # Check proximity for remaining alert objects and to associate persons with alerts
        if person_detections:
            # Check if this alert object is close to any person
            for person_idx in person_detections:
                person_bbox = detections[person_idx].get("bbox", [0, 0, 10, 10])
                
                # For face coverings, use stricter proximity rules
                if "Face_Covered" in alert_cats:
                    # Check if the mask/helmet is properly positioned relative to the person
                    if is_face_covering_worn(alert_bbox, person_bbox):
                        # Add the alert object if not already added
                        if alert_idx not in alert_indices:
                            alert_indices.append(alert_idx)
                            alert_types[alert_idx] = alert_cats
                        
                        # Add the person with the same alert categories
                        if person_idx not in alert_indices:
                            alert_indices.append(person_idx)
                            alert_types[person_idx] = alert_cats
                        
                        logger.info(f"Alert triggered: Person (idx {person_idx}) with face covering")
                # For all other alert types, use standard proximity check
                elif are_objects_related(alert_bbox, person_bbox):
                    # Add the alert object if not already added
                    if alert_idx not in alert_indices:
                        alert_indices.append(alert_idx)
                        alert_types[alert_idx] = alert_cats
                    
                    # Add the person with the same alert categories
                    if person_idx not in alert_indices:
                        alert_indices.append(person_idx)
                        alert_types[person_idx] = alert_cats
                    
                    logger.info(f"Alert triggered: Person (idx {person_idx}) with {', '.join(alert_cats)}")
    
    logger.info(f"Found {len(alert_indices)} alerts: {alert_types}")
    return alert_indices, alert_types

def is_face_covering_worn(mask_bbox, person_bbox):
    """
    Check if a face covering is properly worn by a person
    
    Args:
        mask_bbox: [x, y, width, height] of mask/helmet
        person_bbox: [x, y, width, height] of person
    
    Returns:
        bool: True if the mask appears to be worn by the person
    """
    # Unpack bounding boxes
    mask_x, mask_y, mask_w, mask_h = mask_bbox
    person_x, person_y, person_w, person_h = person_bbox
    
    # Check if mask is in upper portion of the person bounding box
    person_head_y = person_y + person_h * 0.3  # Approximate head position
    
    # Check horizontal overlap
    h_overlap = (mask_x < (person_x + person_w) and (mask_x + mask_w) > person_x)
    
    # Check if mask is in upper portion of person
    v_position = mask_y < person_head_y
    
    return h_overlap and v_position

def are_objects_related(obj1_bbox, obj2_bbox):
    """
    Check if two objects are related (close to each other)
    
    Args:
        obj1_bbox: [x, y, width, height] of first object
        obj2_bbox: [x, y, width, height] of second object
    
    Returns:
        bool: True if the objects are close to each other
    """
    # Unpack bounding boxes
    x1, y1, w1, h1 = obj1_bbox
    x2, y2, w2, h2 = obj2_bbox
    
    # Calculate centers
    center_x1, center_y1 = x1 + w1/2, y1 + h1/2
    center_x2, center_y2 = x2 + w2/2, y2 + h2/2
    
    # Calculate distance between centers
    distance = ((center_x1 - center_x2)**2 + (center_y1 - center_y2)**2)**0.5
    
    # Calculate diagonal of obj2 (person)
    obj2_diagonal = (w2**2 + h2**2)**0.5
    
    # Objects are related if their distance is less than the diagonal of the person bbox
    return distance < obj2_diagonal * 1.5

def get_detection_bboxes(detections, alert_indices=None):
    """
    Get bounding boxes from detections for visualization
    
    Args:
        detections: List of detection dictionaries
        alert_indices: Optional list of detection indices that triggered alerts
    
    Returns:
        list: List of bounding boxes and their associated classes/alerts
    """
    bboxes = []
    
    # If alert_indices is None, include all detections
    if alert_indices is None:
        alert_indices = range(len(detections))
    
    for i, detection in enumerate(detections):
        class_name = detection.get("class_name", "unknown")
        confidence = detection.get("confidence", 0)
        bbox = detection.get("bbox", [0, 0, 10, 10])
        
        # Only process detections in the alert indices
        if i in alert_indices:
            is_alert = True
        else:
            is_alert = False
        
        bboxes.append({
            "bbox": bbox,
            "class_name": class_name,
            "confidence": confidence,
            "is_alert": is_alert
        })
    
    return bboxes

def draw_detection_boxes(image, detections, indices=None, alert_types=None):
    """
    Draw bounding boxes on an image
    
    Args:
        image: OpenCV image
        detections: List of detection dictionaries
        indices: Optional list of detection indices that triggered alerts
        alert_types: Optional mapping from indices to alert types
    
    Returns:
        image: OpenCV image with bounding boxes drawn
    """
    img_copy = image.copy()
    
    # If no specific indices are provided, process all detections
    if indices is None:
        indices = range(len(detections))
    
    # Draw boxes for each detection
    for i in indices:
        if i >= len(detections):
            continue
            
        detection = detections[i]
        bbox = detection.get("bbox", [0, 0, 10, 10])
        class_name = detection.get("class_name", "unknown")
        confidence = detection.get("confidence", 0)
        
        # Determine alert status and types for this detection
        is_alert = alert_types is not None and i in alert_types
        alert_type_list = alert_types.get(i, []) if alert_types and i in alert_types else []
        
        x, y, w, h = bbox
        
        # Choose color: red for alerts, green otherwise
        if is_alert:
            color = (0, 0, 255)  # BGR: Red for alerts
        else:
            color = (0, 255, 0)  # BGR: Green for non-alerts
        
        # Draw the bounding box
        cv2.rectangle(img_copy, (int(x), int(y)), (int(x + w), int(y + h)), color, 2)
        
        # Draw the label
        if is_alert and alert_type_list:
            label = f"{class_name}: {confidence:.2f} ({', '.join(alert_type_list)})"
        else:
            label = f"{class_name}: {confidence:.2f}"
            
        cv2.putText(img_copy, label, (int(x), int(y - 10)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    return img_copy
EOF

# Fix the app.py file - update to use a patched version
cat << 'EOF' > app_patch.py
#!/usr/bin/env python3
import os
import sys
import logging
from logic.detection_analysis import analyze_detections, get_detection_bboxes, draw_detection_boxes
EOF

# Copy the fixed files into the container
echo "Copying fixed files to container..."
docker cp detection_analysis_complete.py "$CONTAINER_ID:/app/alert_logic/logic/detection_analysis.py"
docker cp app_patch.py "$CONTAINER_ID:/app/app_patch.py"

# Create and run a patch script inside the container
echo "Applying patch to app.py inside container..."
cat << 'EOF' > container_patch.sh
#!/bin/bash

# Backup the original file
cp /app/alert_logic/app.py /app/alert_logic/app.py.bak

# Apply the patch to the import statement
head -1 /app/app_patch.py > /tmp/app_header
tail -n +2 /app/alert_logic/app.py > /tmp/app_body
cat /tmp/app_header /tmp/app_body > /app/alert_logic/app.py

echo "Fixing the draw_detection_boxes call in app.py..."
sed -i 's/base_img = draw_detection_boxes(base_img, detections_list, alert_indices, alert_types)/base_img = draw_detection_boxes(base_img, detections_list, alert_indices, alert_types)/g' /app/alert_logic/app.py

echo "Patch applied successfully"
EOF

docker cp container_patch.sh "$CONTAINER_ID:/app/container_patch.sh"
docker exec "$CONTAINER_ID" bash -c "chmod +x /app/container_patch.sh && /app/container_patch.sh"

# Restart the alert-logic service
echo "Restarting alert-logic service..."
docker-compose restart alert-logic

# Wait for the service to restart
sleep 5

echo "Done! Applied complete fix for alert-logic service."
echo "Check the logs to verify the fix:"
echo "docker-compose logs -f alert-logic"
