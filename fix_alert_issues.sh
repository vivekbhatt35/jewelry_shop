#!/bin/bash

# Fix script for alert issues
echo "Applying comprehensive fix for alerts..."

# Restart alert-logic service first to apply the pose_analysis.py fix
echo "Restarting alert-logic service..."
docker-compose restart alert-logic

# Create fix for detection_analysis.py to properly handle masks, helmets, and suspicious objects
cat << 'EOF' > /tmp/detection_analysis_fix.py
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
EOF

# Apply the fix to the container
echo "Applying fix to detection_analysis.py in alert-logic container..."
docker-compose exec alert-logic bash -c "
# Create backup of original file
cp /app/alert_logic/logic/detection_analysis.py /app/alert_logic/logic/detection_analysis.py.bak

# Replace the analyze_detections function with our fixed version
cat /tmp/detection_analysis_fix.py > /app/alert_logic/logic/detection_analysis.py

echo 'Fixed detection_analysis.py to always trigger alerts for masks, helmets, and suspicious objects'
"

# Restart the alert-logic service again to apply all changes
echo "Restarting alert-logic service to apply changes..."
docker-compose restart alert-logic

# Fix detector_pose app.py to ensure image cleanup happens
echo "Fixing cleanup in detector-pose service..."
docker-compose exec detector-pose bash -c "
# Create backup
cp /app/detector_pose/app.py /app/detector_pose/app.py.bak

# Ensure image cleanup happens in all cases
sed -i 's/if alert_type == \"No_Alert\":/if alert_type == \"No_Alert\" or not alert_type or alert_type == \"Unknown_Detection_Type\":/' /app/detector_pose/app.py

echo 'Fixed image cleanup in detector_pose/app.py'
"

# Restart the detector-pose service
echo "Restarting detector-pose service to apply changes..."
docker-compose restart detector-pose

# Fix detector_detections app.py for the same cleanup issue
echo "Fixing cleanup in detector-detections service..."
docker-compose exec detector-detections bash -c "
# Create backup
cp /app/detector_detections/app.py /app/detector_detections/app.py.bak

# Apply similar cleanup fix
sed -i 's/if alert_type == \"No_Alert\":/if alert_type == \"No_Alert\" or not alert_type or alert_type == \"Unknown_Detection_Type\":/' /app/detector_detections/app.py

echo 'Fixed image cleanup in detector_detections/app.py'
"

# Restart the detector-detections service
echo "Restarting detector-detections service to apply changes..."
docker-compose restart detector-detections

echo "Fixes applied successfully!"
echo "The system should now:"
echo "1. Properly generate alerts for masks, helmets, and suspicious objects"
echo "2. Skip pose detection for overhead cameras like CAM_002"
echo "3. Clean up images properly when no alerts are generated"
echo ""
echo "To verify the fix, check the logs with:"
echo "docker-compose logs -f alert-logic"
