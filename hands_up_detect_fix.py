def hands_up_detect(poses_list, camera_id="unknown", camera_angle=None):
    """
    Detect persons with hands up in poses list
    With improved validation for better accuracy and checks for camera angles
    
    Args:
        poses_list: List of poses in format [x1,y1,v1,x2,y2,v2,...] 
                   where each pose has 17 keypoints x 3 values (x,y,v)
    
    Returns:
        list: Indices of persons with hands up
    """
    # IMPORTANT FIX: Check camera_id for overhead or high-angle cameras and disable detection
    if camera_id:
        camera_id_lower = camera_id.lower()
        if (
            "overhead" in camera_id_lower or 
            "ceiling" in camera_id_lower or
            "cam_002" in camera_id_lower  # Specific fix for CAM_002
        ):
            logger.info(f"Hands up detection disabled for overhead camera {camera_id}")
            return []
    
    # For all other cameras, we apply much stricter detection to reduce false positives
    
    alert_indices = []
    
    # Check global throttling
    if not can_trigger_alert("Hands_Up"):
        logger.info(f"Global alert throttling active: Skipping analysis of {len(poses_list)} persons")
        return []
    
    logger.info(f"Analyzing {len(poses_list)} persons for hands up pose with stricter threshold")
    
    # Increase thresholds to reduce false positives
    STRICT_HANDS_UP_HEIGHT_THRESHOLD = 0.25  # Much higher threshold (25% of body height)
    STRICT_CONFIDENCE_THRESHOLD = 0.7  # Higher confidence requirement
    
    # Process each person's pose
    for i, pose in enumerate(poses_list):
        # Rest of the existing code follows
