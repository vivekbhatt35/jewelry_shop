import cv2
import numpy as np
import logging

logger = logging.getLogger("Alert-Logic")

# Define alert types and their associated classes
ALERT_CATEGORIES = {
    "Weapon": ["knife", "scissors", "gun", "pistol", "rifle"],
    "Face_Covered": ["mask", "helmet"],
    "Person": ["person"],
    "Suspicious": ["backpack"]
}

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
    
    logger.info(f"Analyzing {len(detections)} detections")
    
    for i, detection in enumerate(detections):
        class_name = detection.get("class_name", "").lower()
        confidence = detection.get("confidence", 0)
        
        # Skip low confidence detections
        if confidence < 0.35:
            logger.info(f"Detection {i}: {class_name} has low confidence {confidence:.2f}, skipping")
            continue
        
        # Check which category this detection belongs to
        detected_alerts = []
        for alert_type, classes in ALERT_CATEGORIES.items():
            if class_name in [c.lower() for c in classes]:
                detected_alerts.append(alert_type)
                logger.info(f"Detection {i}: {class_name} triggered alert: {alert_type}")
        
        # If we have an alert, add to indices
        if detected_alerts:
            alert_indices.append(i)
            alert_types[i] = detected_alerts
    
    logger.info(f"Found {len(alert_indices)} alerts: {alert_types}")
    return alert_indices, alert_types

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
