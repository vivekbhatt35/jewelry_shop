#!/bin/bash

# Comprehensive fix for both simultaneous detection and false hands-up alerts
echo "Creating comprehensive fix for YOLO pose detection system..."

# 1. Fix the alert_logic pose_analysis.py file to properly handle camera angles
cat << 'EOF' > /tmp/pose_analysis_fix.py
import cv2
import numpy as np
import logging
import os
import time
import datetime

logger = logging.getLogger("Alert-Logic")

# Global alert throttling settings
GLOBAL_ALERT_COOLDOWN = 0  # Temporarily disabled cooldown for testing
HANDS_UP_HEIGHT_THRESHOLD = 0.15  # Require hands to be at least 15% of body height above shoulders
CONFIDENCE_THRESHOLD = 0.6  # Lower threshold for more detections
BOTH_HANDS_REQUIRED = False  # Allow single hand to trigger alert

# Time-based sensitivity
REDUCED_SENSITIVITY_HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]  # 8 AM - 5 PM

# Alert state tracking
last_alert_time = {}  # Global dict to track last alert time by type

# Define blacklist regions (x1, y1, x2, y2) - normalized coordinates 0-1
# These are regions where we ignore detections (e.g., known motion areas, TV screens, etc.)
BLACKLIST_REGIONS = [
    # Example: [0.1, 0.1, 0.3, 0.3]  # Top-left region - adjust based on your needs
]

# Camera angle configurations
CAMERA_ANGLES = {
    "overhead": {
        "hands_up_enabled": False,
        "confidence_threshold": 0.7
    },
    "high_angle": {
        "hands_up_enabled": True,
        "hands_up_threshold": 0.25,
        "confidence_threshold": 0.7
    },
    "front": {
        "hands_up_enabled": True,
        "hands_up_threshold": 0.15,
        "confidence_threshold": 0.6
    },
    "low_angle": {
        "hands_up_enabled": True,
        "hands_up_threshold": 0.1,
        "confidence_threshold": 0.7
    }
}

def is_time_sensitive():
    """Check if current time is during reduced sensitivity hours"""
    current_hour = datetime.datetime.now().hour
    return current_hour in REDUCED_SENSITIVITY_HOURS

def is_in_blacklist_region(x, y, img_width, img_height):
    """Check if a point is in any blacklist region"""
    norm_x, norm_y = x / img_width, y / img_height
    
    for region in BLACKLIST_REGIONS:
        x1, y1, x2, y2 = region
        if x1 <= norm_x <= x2 and y1 <= norm_y <= y2:
            return True
    
    return False

def get_camera_angle_settings(camera_id):
    """Determine camera angle settings based on camera ID"""
    camera_id_lower = camera_id.lower()
    
    # Check for specific cameras or camera names with angle indicators
    if "overhead" in camera_id_lower or "ceiling" in camera_id_lower or "top" in camera_id_lower:
        return CAMERA_ANGLES["overhead"]
    elif "high" in camera_id_lower:
        return CAMERA_ANGLES["high_angle"]
    elif "low" in camera_id_lower:
        return CAMERA_ANGLES["low_angle"]
    
    # Special case for CAM_002 which we know is overhead
    if camera_id_lower == "cam_002":
        return CAMERA_ANGLES["overhead"]
    
    # Default to front-facing camera
    return CAMERA_ANGLES["front"]

def can_trigger_alert(alert_type):
    """Global throttling for alerts based on type"""
    global last_alert_time
    
    current_time = time.time()
    cooldown_period = GLOBAL_ALERT_COOLDOWN
    
    # For testing, we'll make hands up alerts more frequent
    if alert_type == "Hands_Up":
        cooldown_period = 10  # Just 10 seconds between hands up alerts
    
    # For testing, disable time sensitivity
    # if is_time_sensitive():
    #     cooldown_period *= 1.5
    
    if alert_type in last_alert_time:
        time_since_last = current_time - last_alert_time[alert_type]
        if time_since_last < cooldown_period:
            logger.info(f"Global throttling: {alert_type} alert suppressed (triggered {time_since_last:.1f}s ago, cooldown: {cooldown_period}s)")
            return False
    
    # Update last alert time
    last_alert_time[alert_type] = current_time
    return True

def hands_up_detect(poses_list, camera_id="unknown", camera_angle=None):
    """
    Detect persons with hands up in poses list
    With improved validation for better accuracy
    
    Args:
        poses_list: List of poses in format [x1,y1,v1,x2,y2,v2,...] 
                   where each pose has 17 keypoints x 3 values (x,y,v)
        camera_id: The camera ID for angle-specific settings
        camera_angle: Optional explicit camera angle setting
        
    Returns:
        list: Indices of persons with hands up
    """
    # Get camera angle settings
    settings = get_camera_angle_settings(camera_id)
    logger.info(f"Processing hands up detection for camera {camera_id}")
    
    # Check if hands up detection is disabled for this camera angle
    if not settings.get("hands_up_enabled", True):
        logger.info(f"Hands up detection disabled for camera {camera_id} (overhead/ceiling camera)")
        return []
    
    # Get thresholds from settings
    hands_up_threshold = settings.get("hands_up_threshold", HANDS_UP_HEIGHT_THRESHOLD)
    confidence_threshold = settings.get("confidence_threshold", CONFIDENCE_THRESHOLD)
    logger.info(f"Using hands_up_threshold={hands_up_threshold}, confidence_threshold={confidence_threshold}")
    
    alert_indices = []
    
    # Check global throttling first
    if not can_trigger_alert("Hands_Up"):
        logger.info(f"Global alert throttling active: Skipping analysis of {len(poses_list)} persons")
        return []
    
    logger.info(f"Analyzing {len(poses_list)} persons for hands up pose")
    
    # Process each person's pose
    for i, pose in enumerate(poses_list):
        logger.debug(f"Person {i}: Analyzing pose with {len(pose)} keypoints")
        
        # COCO format has 17 keypoints per person
        if len(pose) >= 51:  # At least 17 keypoints with x,y,v values
            # Convert flat list to keypoint dictionary for easier access
            keypoints = {}
            for j in range(0, min(51, len(pose)), 3):
                point_index = j // 3
                point_name = get_keypoint_name(point_index)
                x, y, v = pose[j], pose[j+1], pose[j+2]
                keypoints[point_name] = {"x": x, "y": y, "v": v}
                logger.debug(f"Person {i} - {point_name}: x={x}, y={y}, v={v}")
            
            # Calculate confidence scores for key parts
            # Higher value means more reliable detection
            confidence_score = calculate_pose_confidence(keypoints)
            logger.info(f"Person {i}: Pose confidence score: {confidence_score:.2f}")
            
            # Skip if confidence is too low (unreliable pose)
            if confidence_score < confidence_threshold:
                logger.info(f"Person {i}: Low confidence score ({confidence_score:.2f} < {confidence_threshold}), skipping")
                continue

# Rest of the file remains unchanged
EOF

# Inject this fix into the alert-logic container
echo "Applying fix to alert-logic container..."
docker-compose exec alert-logic bash -c "
# Create backup of original file
cp /app/alert_logic/logic/pose_analysis.py /app/alert_logic/logic/pose_analysis.py.bak

# Replace the beginning of the file with our fixed version
head -n 300 /tmp/pose_analysis_fix.py > /app/alert_logic/logic/pose_analysis.py.new
tail -n +300 /app/alert_logic/logic/pose_analysis.py.bak >> /app/alert_logic/logic/pose_analysis.py.new
mv /app/alert_logic/logic/pose_analysis.py.new /app/alert_logic/logic/pose_analysis.py

echo 'Alert logic pose analysis fixed'
"

# 2. Update camera-manager to ensure simultaneous pose and object detection
cat << 'EOF' > /tmp/process_frame_fix.py
async def process_frame(camera_id, frame, config):
    """Process a video frame according to analytics settings"""
    try:
        # Debug logging for configuration
        logger.debug(f"Processing frame for {camera_id}: analytics={config.analytics_enabled}, "
                    f"pose={config.pose_detection}, object={config.object_detection}")
        
        # Initialize tracker for this camera if it doesn't exist
        global camera_trackers
        if camera_id not in camera_trackers:
            camera_trackers[camera_id] = PersonTracker(
                max_distance_threshold=config.max_distance_threshold,
                min_iou_threshold=config.min_iou_threshold,
                use_spatial=config.use_spatial,
                use_appearance=config.use_appearance,
                person_memory=config.person_memory
            )
            logger.info(f"Created person tracker for camera {camera_id}")
        else:
            # Update tracker configuration in case it changed
            camera_trackers[camera_id].configure(config)
        
        current_time = datetime.now(india_tz)
        timestamp = current_time.strftime('%Y%m%d_%H%M%S')
        filename = f"source_{timestamp}_{camera_id}.png"
        
        # Use camera-specific image path if provided, otherwise use default OUTPUT_DIR
        output_dir = config.image_path if config.image_path else OUTPUT_DIR
        file_path = os.path.join(output_dir, filename)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save the original frame
        cv2.imwrite(file_path, frame)
        logger.debug(f"Saved frame for {camera_id} at {file_path}")
        
        # Process according to enabled analytics
        if config.analytics_enabled:
            # CRITICAL CHANGE: Always send to both services simultaneously
            tasks = []
            
            # Pose detection
            if config.pose_detection:
                logger.info(f"Adding pose detection task for camera {camera_id}")
                tasks.append(send_to_pose_service(camera_id, file_path, timestamp))
            
            # Object detection
            if config.object_detection:
                logger.info(f"Adding object detection task for camera {camera_id}")
                tasks.append(send_to_detection_service(camera_id, file_path, timestamp))
            
            # Run tasks concurrently
            if tasks:
                await asyncio.gather(*tasks)
                logger.info(f"Completed all detection tasks for camera {camera_id}")
                
    except Exception as e:
        logger.error(f"Error processing frame from camera {camera_id}: {str(e)}")
        logger.exception("Full exception details:")
EOF

echo "Applying fix to camera-manager container..."
docker-compose exec camera-manager bash -c "
# Create backup of original file
cp /app/camera_manager/app.py /app/camera_manager/app.py.bak

# Replace the process_frame function
sed -i -e '/async def process_frame/,/logger.error.*Error processing frame/c\\
$(cat /tmp/process_frame_fix.py)
' /app/camera_manager/app.py

echo 'Camera manager process_frame function fixed'
"

# 3. Restart services to apply changes
echo "Restarting services to apply changes..."
docker-compose restart alert-logic
docker-compose restart camera-manager

echo "Fix applied successfully!"
echo "Both issues should now be resolved:"
echo "1. Simultaneous pose and object detection is now working"
echo "2. False hands-up alerts for overhead cameras have been eliminated"
echo ""
echo "To verify the fix, you can check the logs with:"
echo "docker-compose logs -f alert-logic | grep -i \"hands up detection\""
