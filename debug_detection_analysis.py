#!/usr/bin/env python3
"""
Direct test script for weapon detection alert logic.
This script directly tests the weapon detection alert logic
to ensure it's correctly identifying weapon objects and generating alerts.
"""
import sys
import os
import json
import logging
from alert_logic.logic.detection_analysis import (
    analyze_detections,
    ALERT_CATEGORIES,
    CRITICAL_CLASSES
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DebugScript")

# Print configuration
logger.info("Alert Categories:")
for category, classes in ALERT_CATEGORIES.items():
    logger.info(f"  - {category}: {classes}")

logger.info("\nCritical Classes:")
logger.info(f"  - {CRITICAL_CLASSES}")

def test_weapon_detection():
    """Test if the weapon detection is working correctly."""
    logger.info("Starting weapon detection test")
    
    detections = []
    
    # Test case 1: Single person with weapon class
    logger.info("\nTest Case 1: Single 'person with weapon' detection")
    detections = [{
        "class_name": "person with weapon",
        "confidence": 0.85,
        "bbox": [100, 100, 300, 400]
    }]
    
    alert_indices, alert_types = analyze_detections(detections)
    logger.info(f"Alert indices: {alert_indices}")
    logger.info(f"Alert types: {alert_types}")
    logger.info(f"Alert generated: {len(alert_indices) > 0}")
    
    # Test case 2: Gun detection
    logger.info("\nTest Case 2: Gun detection")
    detections = [{
        "class_name": "gun",
        "confidence": 0.75,
        "bbox": [150, 150, 250, 200]
    }]
    
    alert_indices, alert_types = analyze_detections(detections)
    logger.info(f"Alert indices: {alert_indices}")
    logger.info(f"Alert types: {alert_types}")
    logger.info(f"Alert generated: {len(alert_indices) > 0}")
    
    # Test case 3: Gun with low confidence
    logger.info("\nTest Case 3: Gun with low confidence")
    detections = [{
        "class_name": "gun",
        "confidence": 0.30,  # Below threshold
        "bbox": [150, 150, 250, 200]
    }]
    
    alert_indices, alert_types = analyze_detections(detections)
    logger.info(f"Alert indices: {alert_indices}")
    logger.info(f"Alert types: {alert_types}")
    logger.info(f"Alert generated: {len(alert_indices) > 0}")
    
    # Test case 4: Person and gun separately
    logger.info("\nTest Case 4: Person and gun separately")
    detections = [
        {
            "class_name": "person",
            "confidence": 0.90,
            "bbox": [100, 100, 300, 400]
        },
        {
            "class_name": "gun",
            "confidence": 0.75,
            "bbox": [150, 150, 250, 200]
        }
    ]
    
    alert_indices, alert_types = analyze_detections(detections)
    logger.info(f"Alert indices: {alert_indices}")
    logger.info(f"Alert types: {alert_types}")
    logger.info(f"Alert generated: {len(alert_indices) > 0}")

if __name__ == "__main__":
    test_weapon_detection()
