#!/bin/bash

# Direct fix for detection_analysis.py
echo "Applying direct fix for detection_analysis.py..."

# Create fix file directly in the container
docker-compose exec alert-logic bash -c "cat > /app/alert_logic/logic/detection_analysis.py << 'EOF'
import cv2
import numpy as np
import logging

logger = logging.getLogger(\"Alert-Logic\")

# Define alert types and their associated classes
ALERT_CATEGORIES = {
    \"Weapon\": [\"weapon\"],
    \"Face_Covered\": [\"mask\", \"helmet\"],
    \"Suspicious\": [\"suspicious\"]
}

# Define classes that are monitored but don't trigger alerts by themselves
MONITORED_CLASSES = [\"person\"]

# Define critical classes that always trigger alerts regardless of other conditions
CRITICAL_CLASSES = [\"weapon\", \"mask\", \"helmet\", \"suspicious\"]

def analyze_detections(detections):
    \"\"\"
    Analyze object detections to identify items of interest
    
    Args:
        detections: List of detection dictionaries with class_name, confidence, bbox
    
    Returns:
        list: Indices of detections that trigger alerts
        dict: Mapping of detection indices to alert types
    \"\"\"
    alert_indices = []
    alert_types = {}
    
    # Track persons and alert objects separately
    person_detections = []
    alert_detections = {}
    
    logger.info(f\"Analyzing {len(detections)} detections\")
    
    # First pass: identify all persons and alert objects
    for i, detection in enumerate(detections):
        class_name = detection.get(\"class_name\", \"\").lower()
        confidence = detection.get(\"confidence\", 0)
        
        # Define thresholds by class type
        if class_name == \"weapon\":
            threshold = 0.10  # Very low threshold for weapons
            logger.info(f\"Using weapon threshold of {threshold} for {class_name}\")
        elif class_name == \"suspicious\":
            threshold = 0.25  # Low threshold for suspicious items
            logger.info(f\"Using suspicious threshold of {threshold} for {class_name}\")
        elif class_name == \"mask\" or class_name == \"helmet\":
            threshold = 0.30  # Medium-low threshold for masks/helmets
            logger.info(f\"Using mask/helmet threshold of {threshold} for {class_name}\")
        else:
            threshold = 0.35  # Normal threshold for everything else
        
        # Skip low confidence detections
        if confidence < threshold:
            logger.info(f\"Detection {i}: {class_name} has low confidence {confidence:.2f}, threshold {threshold}, skipping\")
            continue
        
        # CRITICAL FIX: Direct alerts for critical classes
        if class_name.lower() in [c.lower() for c in CRITICAL_CLASSES]:
            # Determine the alert type for this detection
            alert_type = None
            if class_name.lower() == \"weapon\":
                alert_type = \"Weapon\"
            elif class_name.lower() in [\"mask\", \"helmet\"]:
                alert_type = \"Face_Covered\"
            elif class_name.lower() == \"suspicious\":
                alert_type = \"Suspicious\"
            
            # Add to alert indices directly - this is an immediate alert
            if alert_type:
                alert_indices.append(i)
                alert_types[i] = [alert_type]
                logger.info(f\"CRITICAL DETECTION: {i}: {class_name} directly triggered {alert_type} alert with confidence {confidence:.2f}\")
        
        # Track person detections
        if class_name == \"person\":
            person_detections.append(i)
        
        # Check which category this detection belongs to for other classes
        detected_alerts = []
        for alert_type, classes in ALERT_CATEGORIES.items():
            if class_name in [c.lower() for c in classes]:
                detected_alerts.append(alert_type)
                logger.info(f\"Detection {i}: {class_name} triggered alert: {alert_type}\")
        
        # If this is an alert object that's not already triggered, store it
        if detected_alerts and i not in alert_indices:
            alert_detections[i] = detected_alerts
    
    logger.info(f\"Found {len(person_detections)} persons and {len(alert_detections)} alert objects\")
    
    # Second pass: handle associations between persons and alert objects
    for alert_idx, alert_cats in alert_detections.items():
        # Skip if this alert was already triggered in the first pass
        if alert_idx in alert_indices:
            continue
            
        alert_bbox = detections[alert_idx].get(\"bbox\", [0, 0, 10, 10])
        class_name = detections[alert_idx].get(\"class_name\", \"\").lower()
        
        # Check proximity for remaining alert objects and to associate persons with alerts
        if person_detections:
            # Check if this alert object is close to any person
            for person_idx in person_detections:
                person_bbox = detections[person_idx].get(\"bbox\", [0, 0, 10, 10])
                
                # For face coverings, use stricter proximity rules
                if \"Face_Covered\" in alert_cats:
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
                        
                        logger.info(f\"Alert triggered: Person (idx {person_idx}) with face covering\")
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
                    
                    logger.info(f\"Alert triggered: Person (idx {person_idx}) with {', '.join(alert_cats)}\")
    
    logger.info(f\"Found {len(alert_indices)} alerts: {alert_types}\")
    return alert_indices, alert_types

def is_face_covering_worn(mask_bbox, person_bbox):
    \"\"\"
    Determine if a face covering is properly worn by a person
    by checking if the mask/helmet is in the upper portion of the person bbox
    and has significant overlap with where a face would typically be
    
    Args:
        mask_bbox: Bounding box of mask/helmet as [x1, y1, x2, y2]
        person_bbox: Bounding box of person as [x1, y1, x2, y2]
    
    Returns:
        bool: True if the face covering appears to be worn, False otherwise
    \"\"\"
    # Unpack bounding boxes
    mx1, my1, mx2, my2 = mask_bbox
    px1, py1, px2, py2 = person_bbox
    
    # Calculate dimensions
    person_height = py2 - py1
    person_width = px2 - px1
    mask_height = my2 - my1
    mask_width = mx2 - mx1
    
    # Skip if either box has invalid dimensions
    if person_height <= 0 or person_width <= 0 or mask_height <= 0 or mask_width <= 0:
        return False
        
    # 1. Check if mask is in upper 1/3 of person bounding box
    person_upper_third = py1 + person_height/3
    if my2 < py1 or my1 > person_upper_third:
        return False  # Mask is not in upper third of person
    
    # 2. Check horizontal alignment (mask should be centered within person width)
    mask_center_x = (mx1 + mx2) / 2
    person_center_x = (px1 + px2) / 2
    horizontal_offset = abs(mask_center_x - person_center_x) / person_width
    if horizontal_offset > 0.3:  # Allow some offset, but not too much
        return False  # Mask is too far to the side
    
    # 3. Size check - mask shouldn't be too large compared to person
    if mask_width > person_width * 0.8 or mask_height > person_height * 0.5:
        return False  # Mask is unrealistically large
    
    # 4. Check for reasonable overlap
    # Calculate intersection
    x_left = max(mx1, px1)
    y_top = max(my1, py1)
    x_right = min(mx2, px2)
    y_bottom = min(my2, py2)
    
    if x_right > x_left and y_bottom > y_top:
        intersection = (x_right - x_left) * (y_bottom - y_top)
        mask_area = mask_width * mask_height
        
        # Mask should have significant overlap with person
        if intersection / mask_area < 0.5:
            return False  # Not enough overlap
    else:
        return False  # No overlap
    
    # All checks passed
    return True

def are_objects_related(bbox1, bbox2, overlap_threshold=0.3, proximity_threshold=100):
    \"\"\"
    Determine if two objects are related based on overlap or proximity
    
    Args:
        bbox1, bbox2: Bounding boxes as [x1, y1, x2, y2]
        overlap_threshold: Minimum overlap ratio to consider objects related
        proximity_threshold: Maximum distance in pixels to consider objects related
    
    Returns:
        bool: True if objects are related, False otherwise
    \"\"\"
    # Check for overlap
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    # Calculate intersection
    x_left = max(x1_1, x1_2)
    y_top = max(y1_1, y1_2)
    x_right = min(x2_1, x2_2)
    y_bottom = min(y2_1, y2_2)
    
    # If boxes overlap
    if x_right > x_left and y_bottom > y_top:
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        smaller_area = min(area1, area2)
        
        if intersection / smaller_area > overlap_threshold:
            return True
    
    # Check for proximity if they don't overlap significantly
    # Calculate centers
    center1_x = (x1_1 + x2_1) / 2
    center1_y = (y1_1 + y2_1) / 2
    center2_x = (x1_2 + x2_2) / 2
    center2_y = (y1_2 + y2_2) / 2
    
    # Calculate Euclidean distance
    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
    
    return distance < proximity_threshold

def get_detection_bboxes(detections):
    \"\"\"
    Extract bounding boxes from detection list
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        list: Bounding boxes as [x1, y1, x2, y2]
    \"\"\"
    return [detection.get(\"bbox\", [0, 0, 10, 10]) for detection in detections]

def draw_detection_boxes(image, detections, indices=None, alert_types=None):
    \"\"\"
    Draw bounding boxes on image for detected objects with their alert types
    
    Args:
        image: OpenCV image
        detections: List of detection dictionaries
        indices: Indices of detections to draw, if None, draw all
        alert_types: Dictionary mapping indices to alert types
    
    Returns:
        image: Image with boxes drawn
    \"\"\"
    result_image = image.copy()
    
    if indices is None:
        indices = range(len(detections))
    
    if alert_types is None:
        alert_types = {}
    
    for idx in indices:
        if idx < len(detections):
            detection = detections[idx]
            bbox = detection.get(\"bbox\", [0, 0, 0, 0])
            class_name = detection.get(\"class_name\", \"\")
            conf = detection.get(\"confidence\", 0)
            
            if len(bbox) < 4 or (bbox[0] == 0 and bbox[1] == 0 and bbox[2] == 0 and bbox[3] == 0):
                continue
                
            x1, y1, x2, y2 = bbox
            
            # Set color based on alert type
            color = (0, 255, 0)  # Default green for non-alert objects
            
            # If this detection has alert types, use them to determine color
            if idx in alert_types:
                alerts = alert_types[idx]
                if \"Weapon\" in alerts:
                    color = (0, 0, 255)  # Red for weapons
                elif \"Face_Covered\" in alerts:
                    color = (255, 0, 0)  # Blue for face coverings
                elif \"Suspicious\" in alerts:
                    color = (0, 165, 255)  # Orange for suspicious items
            
            # Draw rectangle with thicker border for alert objects
            thickness = 3 if idx in alert_types else 1
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
            
            # Prepare label text with alert types
            label_text = f\"{class_name} {conf:.2f}\"
            if idx in alert_types:
                if class_name.lower() == \"person\":
                    # For persons, show what alert they're associated with
                    alert_text = \", \".join(alert_types[idx])
                    label_text = f\"Person with {alert_text}\"
                else:
                    # For alert objects, show the alert type
                    alert_text = \", \".join(alert_types[idx])
                    label_text = f\"{alert_text}: {label_text}\"
            
            # Draw label background
            text_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(result_image, 
                         (x1, y1 - text_size[1] - 10), 
                         (x1 + text_size[0], y1), 
                         color, -1)
            
            # Draw label text
            cv2.putText(result_image, label_text, 
                       (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return result_image
EOF"

# Restart the alert-logic service
echo "Restarting alert-logic service to apply the fix..."
docker-compose restart alert-logic

# Verify that the fix was applied
echo "Checking if the fix was applied correctly..."
docker-compose exec alert-logic bash -c "grep -q CRITICAL_CLASSES /app/alert_logic/logic/detection_analysis.py && echo 'Fix applied successfully!' || echo 'Fix failed!'"

echo ""
echo "The system should now generate alerts for:"
echo "1. Masks (Face_Covered alert)"
echo "2. Helmets (Face_Covered alert)"
echo "3. Suspicious objects (Suspicious alert)"
echo "4. Weapons (already working)"
echo ""
echo "To verify the fix, check the logs with:"
echo "docker-compose logs -f alert-logic"
