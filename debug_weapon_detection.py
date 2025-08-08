#!/usr/bin/env python3
"""
Debug script to test the detection_analysis module directly
This script allows you to validate that the alert_logic correctly identifies weapon detections
"""
import os
import sys
import json
import logging
import cv2
import numpy as np
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Alert-Debug")

# Add the project root to the path so we can import from the project modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import the detection analysis module
try:
    from alert_logic.logic.detection_analysis import analyze_detections, draw_detection_boxes, ALERT_CATEGORIES
    logger.info("Successfully imported detection_analysis module")
    logger.info(f"Alert categories: {ALERT_CATEGORIES}")
except ImportError as e:
    logger.error(f"Failed to import detection_analysis: {e}")
    sys.exit(1)

def create_test_image(width=640, height=480):
    """Create a test image with person and weapon"""
    img = np.ones((height, width, 3), dtype=np.uint8) * 200  # Light gray
    
    # Draw a person rectangle
    cv2.rectangle(img, (50, 50), (200, 400), (255, 0, 0), 2)  # Blue
    cv2.putText(img, "Person", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Draw a weapon rectangle
    cv2.rectangle(img, (250, 150), (400, 350), (0, 0, 255), 2)  # Red
    cv2.putText(img, "Person with weapon", (250, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    return img

def test_weapon_detection():
    """Test detection analysis with weapon classes"""
    
    # Create test detections for both standard weapon classes and "person with weapon" class
    test_detections = [
        # Test 1: Standard person
        {
            "class_name": "person",
            "confidence": 0.95,
            "bbox": [50, 50, 200, 400]
        },
        # Test 2: Standard weapon (gun)
        {
            "class_name": "gun",
            "confidence": 0.85,
            "bbox": [210, 150, 240, 190]
        },
        # Test 3: New "person with weapon" class
        {
            "class_name": "person with weapon",
            "confidence": 0.88,
            "bbox": [250, 150, 400, 350]
        }
    ]
    
    logger.info("Testing standard weapon detection...")
    alert_indices, alert_types = analyze_detections(test_detections[:2])
    logger.info(f"Standard weapon results - Alert indices: {alert_indices}")
    logger.info(f"Standard weapon results - Alert types: {alert_types}")
    
    logger.info("\nTesting 'person with weapon' detection...")
    alert_indices2, alert_types2 = analyze_detections([test_detections[0], test_detections[2]])
    logger.info(f"'Person with weapon' results - Alert indices: {alert_indices2}")
    logger.info(f"'Person with weapon' results - Alert types: {alert_types2}")
    
    # Create visual output to see the results
    test_img = create_test_image()
    result_img1 = draw_detection_boxes(test_img.copy(), test_detections[:2], alert_indices, alert_types)
    result_img2 = draw_detection_boxes(test_img.copy(), [test_detections[0], test_detections[2]], 
                                     alert_indices2, alert_types2)
    
    # Save the result images
    cv2.imwrite("debug_standard_weapon_detection.jpg", result_img1)
    cv2.imwrite("debug_person_with_weapon_detection.jpg", result_img2)
    
    logger.info("\nSaved debug images:")
    logger.info("- debug_standard_weapon_detection.jpg")
    logger.info("- debug_person_with_weapon_detection.jpg")
    
    # Report success or failure
    if alert_indices and any("Weapon" in alert_types.get(idx, []) for idx in alert_indices):
        logger.info("SUCCESS: Standard weapon detection worked!")
    else:
        logger.warning("FAIL: Standard weapon detection failed!")
        
    if alert_indices2 and any("Weapon" in alert_types2.get(idx, []) for idx in alert_indices2):
        logger.info("SUCCESS: 'Person with weapon' detection worked!")
    else:
        logger.warning("FAIL: 'Person with weapon' detection failed!")

if __name__ == "__main__":
    logger.info("Starting weapon detection debug test")
    test_weapon_detection()
    logger.info("Test completed")
