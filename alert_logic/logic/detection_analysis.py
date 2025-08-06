import cv2
import numpy as np
import logging

logger = logging.getLogger("Alert-Logic")

# Define alert types and their associated classes
ALERT_CATEGORIES = {
    "Weapon": ["knife", "scissors", "gun", "pistol", "rifle"],
    "Face_Covered": ["mask", "helmet"],
    "Suspicious": ["backpack"]
}

# Define classes that are monitored but don't trigger alerts by themselves
MONITORED_CLASSES = ["person"]

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
        
        # Skip low confidence detections
        if confidence < 0.35:
            logger.info(f"Detection {i}: {class_name} has low confidence {confidence:.2f}, skipping")
            continue
        
        # Track person detections separately
        if class_name == "person":
            person_detections.append(i)
            continue
        
        # Check which category this detection belongs to
        detected_alerts = []
        for alert_type, classes in ALERT_CATEGORIES.items():
            if class_name in [c.lower() for c in classes]:
                detected_alerts.append(alert_type)
                logger.info(f"Detection {i}: {class_name} triggered alert: {alert_type}")
        
        # If this is an alert object, store it
        if detected_alerts:
            alert_detections[i] = detected_alerts
    
    logger.info(f"Found {len(person_detections)} persons and {len(alert_detections)} alert objects")
    
    # Second pass: check for proximity between persons and alert objects
    if alert_detections and person_detections:
        for alert_idx, alert_cats in alert_detections.items():
            alert_bbox = detections[alert_idx].get("bbox", [0, 0, 10, 10])
            
            # Check if this alert object is close to any person
            for person_idx in person_detections:
                person_bbox = detections[person_idx].get("bbox", [0, 0, 10, 10])
                
                # If the alert object is within or near a person's bounding box, add both to alerts
                if are_objects_related(alert_bbox, person_bbox):
                    # Add the alert object
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

def are_objects_related(bbox1, bbox2, overlap_threshold=0.3, proximity_threshold=100):
    """
    Determine if two objects are related based on overlap or proximity
    
    Args:
        bbox1, bbox2: Bounding boxes as [x1, y1, x2, y2]
        overlap_threshold: Minimum overlap ratio to consider objects related
        proximity_threshold: Maximum distance in pixels to consider objects related
    
    Returns:
        bool: True if objects are related, False otherwise
    """
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
    """
    Extract bounding boxes from detection list
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        list: Bounding boxes as [x1, y1, x2, y2]
    """
    return [detection.get("bbox", [0, 0, 10, 10]) for detection in detections]

def draw_detection_boxes(image, detections, indices=None, alert_types=None):
    """
    Draw bounding boxes on image for detected objects with their alert types
    
    Args:
        image: OpenCV image
        detections: List of detection dictionaries
        indices: Indices of detections to draw, if None, draw all
        alert_types: Dictionary mapping indices to alert types
    
    Returns:
        image: Image with boxes drawn
    """
    result_image = image.copy()
    
    if indices is None:
        indices = range(len(detections))
    
    if alert_types is None:
        alert_types = {}
    
    for idx in indices:
        if idx < len(detections):
            detection = detections[idx]
            bbox = detection.get("bbox", [0, 0, 0, 0])
            class_name = detection.get("class_name", "")
            conf = detection.get("confidence", 0)
            
            if len(bbox) < 4 or (bbox[0] == 0 and bbox[1] == 0 and bbox[2] == 0 and bbox[3] == 0):
                continue
                
            x1, y1, x2, y2 = bbox
            
            # Set color based on alert type
            color = (0, 255, 0)  # Default green for non-alert objects
            
            # If this detection has alert types, use them to determine color
            if idx in alert_types:
                alerts = alert_types[idx]
                if "Weapon" in alerts:
                    color = (0, 0, 255)  # Red for weapons
                elif "Face_Covered" in alerts:
                    color = (255, 0, 0)  # Blue for face coverings
                elif "Suspicious" in alerts:
                    color = (0, 165, 255)  # Orange for suspicious items
            
            # Draw rectangle with thicker border for alert objects
            thickness = 3 if idx in alert_types else 1
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
            
            # Prepare label text with alert types
            label_text = f"{class_name} {conf:.2f}"
            if idx in alert_types:
                if class_name.lower() == "person":
                    # For persons, show what alert they're associated with
                    alert_text = ", ".join(alert_types[idx])
                    label_text = f"Person with {alert_text}"
                else:
                    # For alert objects, show the alert type
                    alert_text = ", ".join(alert_types[idx])
                    label_text = f"{alert_text}: {label_text}"
            
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
