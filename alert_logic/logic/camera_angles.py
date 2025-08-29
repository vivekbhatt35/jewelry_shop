"""
Camera angle configuration for pose analysis.
This module provides functions to adjust pose detection based on camera angles.
"""

import logging

logger = logging.getLogger("Alert-Logic")

# Define camera angle types
CAMERA_ANGLES = {
    "front": {
        "description": "Camera at eye level facing straight",
        "hands_up_threshold": 0.15,  # Hands must be 15% of body height above shoulders
        "confidence_threshold": 0.6,
    },
    "overhead": {
        "description": "Camera mounted on ceiling facing down",
        "hands_up_threshold": 0.0,  # Disable hands up detection for overhead cameras
        "confidence_threshold": 0.7,  # Higher confidence for overhead views
    },
    "high_angle": {
        "description": "Camera mounted high but at an angle",
        "hands_up_threshold": 0.25,  # Require higher hands for high-angle cameras
        "confidence_threshold": 0.65,
    },
    "low_angle": {
        "description": "Camera mounted below eye level looking up",
        "hands_up_threshold": 0.1,  # Lower threshold for low-angle cameras
        "confidence_threshold": 0.65,
    }
}

def get_camera_angle_settings(camera_id):
    """
    Get camera angle settings based on camera ID.
    This function can be extended to use a database or configuration file.
    
    Args:
        camera_id: The ID of the camera
        
    Returns:
        dict: Camera angle settings
    """
    # Default to front-facing camera
    angle_type = "front"
    
    # Check for specific camera IDs with known angles
    if camera_id.endswith("_overhead") or "_overhead_" in camera_id:
        angle_type = "overhead"
    elif camera_id.endswith("_high") or "_high_" in camera_id:
        angle_type = "high_angle"
    elif camera_id.endswith("_low") or "_low_" in camera_id:
        angle_type = "low_angle"
    
    logger.debug(f"Camera {camera_id} using angle type: {angle_type}")
    return CAMERA_ANGLES.get(angle_type, CAMERA_ANGLES["front"])

def adjust_hands_up_threshold(camera_id, camera_angle=None):
    """
    Adjust hands up threshold based on camera angle.
    
    Args:
        camera_id: The ID of the camera
        camera_angle: Optional explicit camera angle type
        
    Returns:
        float: Adjusted threshold value
    """
    if camera_angle and camera_angle.lower() in CAMERA_ANGLES:
        settings = CAMERA_ANGLES[camera_angle.lower()]
    else:
        settings = get_camera_angle_settings(camera_id)
    
    return settings["hands_up_threshold"]

def adjust_confidence_threshold(camera_id, camera_angle=None):
    """
    Adjust confidence threshold based on camera angle.
    
    Args:
        camera_id: The ID of the camera
        camera_angle: Optional explicit camera angle type
        
    Returns:
        float: Adjusted confidence value
    """
    if camera_angle and camera_angle.lower() in CAMERA_ANGLES:
        settings = CAMERA_ANGLES[camera_angle.lower()]
    else:
        settings = get_camera_angle_settings(camera_id)
    
    return settings["confidence_threshold"]

def is_hands_up_disabled(camera_id, camera_angle=None):
    """
    Check if hands up detection should be disabled for this camera.
    
    Args:
        camera_id: The ID of the camera
        camera_angle: Optional explicit camera angle type
        
    Returns:
        bool: True if hands up detection should be disabled
    """
    hands_up_threshold = adjust_hands_up_threshold(camera_id, camera_angle)
    
    # Threshold of 0 means disable hands up detection
    return hands_up_threshold <= 0
