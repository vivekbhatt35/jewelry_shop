import cv2
import numpy as np
import logging

logger = logging.getLogger("Alert-Logic")

# Define alert types and their associated classes - Updated for new class structure
ALERT_CATEGORIES = {
    "Weapon": ["weapon"],
    "Face_Covered": ["mask", "helmet"],
    "Suspicious": ["suspicious"]
}

# Define classes that are monitored but don't trigger alerts by themselves
MONITORED_CLASSES = ["person"]

# Define critical classes that always trigger alerts regardless of other conditions
CRITICAL_CLASSES = ["weapon"]

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
        
        # Use an EXTREMELY low threshold for weapons (0.10) and regular threshold for other objects (0.35)
        is_weapon = any(weapon.lower() in class_name.lower() for weapon in CRITICAL_CLASSES)
        is_weapon_related = any(weapon.lower() in class_name.lower() for weapon in ALERT_CATEGORIES["Weapon"])
        
        if is_weapon:
            threshold = 0.10  # Extremely low threshold for critical weapons
            logger.info(f"Using critical weapon threshold of {threshold} for {class_name}")
        elif is_weapon_related:
            threshold = 0.15  # Very low threshold for weapon-related items
            logger.info(f"Using weapon-related threshold of {threshold} for {class_name}")
        else:
            threshold = 0.35  # Normal threshold for everything else
        
        # Skip low confidence detections
        if confidence < threshold:
            logger.info(f"Detection {i}: {class_name} has low confidence {confidence:.2f}, threshold {threshold}, skipping")
            continue
        
        # Special case for weapons - always trigger an immediate alert
        if class_name.lower() in [c.lower() for c in CRITICAL_CLASSES]:
            # Add to alert indices directly - this is an immediate alert
            alert_indices.append(i)
            alert_types[i] = ["Weapon"]
            logger.info(f"CRITICAL DETECTION: {i}: {class_name} directly triggered Weapon alert")
            # Continue to process this detection for additional alerts
            
        # Check which category this detection belongs to
        detected_alerts = []
        for alert_type, classes in ALERT_CATEGORIES.items():
            if class_name in [c.lower() for c in classes]:
                detected_alerts.append(alert_type)
                logger.info(f"Detection {i}: {class_name} triggered alert: {alert_type}")
                
                    # RELAXED LOGIC: Immediately trigger an alert for any weapon
                if alert_type == "Weapon":
                    if i not in alert_indices:
                        alert_indices.append(i)
                    if i not in alert_types:
                        alert_types[i] = []
                    if "Weapon" not in alert_types[i]:
                        alert_types[i].append("Weapon")
                    logger.warning(f"HIGH PRIORITY: {class_name} directly triggered Weapon alert with confidence {detection.get('confidence', 0):.2f}")        # Track person detections
        if class_name == "person":
            person_detections.append(i)
            # RELAXED LOGIC: Add person directly to alerts (optional)
            # alert_indices.append(i)
            # alert_types[i] = ["Person_Alert"]
            # logger.info(f"Relaxed logic: Person directly triggered alert")
        
        # If this is an alert object that's not already triggered, store it
        if detected_alerts and i not in alert_indices:
            alert_detections[i] = detected_alerts
    
    logger.info(f"Found {len(person_detections)} persons and {len(alert_detections)} alert objects")
    
    # Second pass: handle remaining alert objects and check for specific combinations
    for alert_idx, alert_cats in alert_detections.items():
        # Skip if this alert was already triggered in the first pass (weapons)
        if alert_idx in alert_indices:
            continue
            
        alert_bbox = detections[alert_idx].get("bbox", [0, 0, 10, 10])
        class_name = detections[alert_idx].get("class_name", "").lower()
        
        # Face covering alerts now require proximity to a person
        # They will be handled in the person proximity check below
        # No longer triggering face covering alerts independently
                
        # Check proximity for remaining suspicious items and to associate persons with alerts
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
    Determine if a face covering is properly worn by a person
    by checking if the mask/helmet is in the upper portion of the person bbox
    and has significant overlap with where a face would typically be
    
    Args:
        mask_bbox: Bounding box of mask/helmet as [x1, y1, x2, y2]
        person_bbox: Bounding box of person as [x1, y1, x2, y2]
    
    Returns:
        bool: True if the face covering appears to be worn, False otherwise
    """
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
