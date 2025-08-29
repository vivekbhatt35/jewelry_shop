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
                
            # Check if either hand is raised
            left_hand_up = is_hand_raised(keypoints, "left", hands_up_threshold)
            right_hand_up = is_hand_raised(keypoints, "right", hands_up_threshold)
            
            # Decide if this is a hands up pose
            # If we require both hands up, check both. Otherwise, check if either hand is up
            if BOTH_HANDS_REQUIRED and left_hand_up and right_hand_up:
                logger.info(f"Person {i}: BOTH hands up detected")
                alert_indices.append(i)
            elif not BOTH_HANDS_REQUIRED and (left_hand_up or right_hand_up):
                logger.info(f"Person {i}: Hand(s) up detected (Left: {left_hand_up}, Right: {right_hand_up})")
                alert_indices.append(i)
    
    # Return indices of persons with hands up
    logger.info(f"Found {len(alert_indices)} persons with hands up")
    return alert_indices

def get_keypoint_name(index):
    """Map keypoint index to name"""
    # COCO keypoints: https://cocodataset.org/#keypoints-2020
    keypoint_names = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    if 0 <= index < len(keypoint_names):
        return keypoint_names[index]
    return f"unknown_{index}"

def calculate_pose_confidence(keypoints):
    """
    Calculate overall confidence score for the pose
    Weighted average of visibilities for key points
    
    Args:
        keypoints: Dictionary of keypoints
        
    Returns:
        float: Confidence score 0.0-1.0
    """
    key_points = ["nose", "left_shoulder", "right_shoulder", 
                 "left_elbow", "right_elbow", "left_wrist", "right_wrist"]
    
    confidences = []
    weights = []
    
    for point in key_points:
        if point in keypoints:
            visibility = keypoints[point]["v"]
            
            # Higher weight for shoulders and wrists (more important for hands up detection)
            weight = 2.0 if "shoulder" in point or "wrist" in point else 1.0
            confidences.append(visibility * weight)
            weights.append(weight)
    
    # If no valid keypoints found, return 0
    if not confidences:
        return 0.0
    
    # Weighted average
    return sum(confidences) / sum(weights) if sum(weights) > 0 else 0.0

def is_hand_raised(keypoints, side, height_threshold):
    """
    Check if hand (wrist) is raised above shoulder
    
    Args:
        keypoints: Dictionary of keypoints
        side: "left" or "right"
        height_threshold: Minimum vertical distance as percentage of body height
        
    Returns:
        bool: True if hand is raised, False otherwise
    """
    shoulder_key = f"{side}_shoulder"
    elbow_key = f"{side}_elbow"
    wrist_key = f"{side}_wrist"
    
    # Need shoulder and wrist at minimum
    if not all(k in keypoints for k in [shoulder_key, wrist_key]):
        return False
    
    shoulder = keypoints[shoulder_key]
    wrist = keypoints[wrist_key]
    
    # Check visibility/confidence thresholds
    if shoulder["v"] < 0.5 or wrist["v"] < 0.5:
        return False
    
    # Check if wrist is above shoulder
    if wrist["y"] >= shoulder["y"]:  # y increases downward in image
        return False
    
    # If elbow is available, do some additional validation
    if elbow_key in keypoints and keypoints[elbow_key]["v"] > 0.3:
        elbow = keypoints[elbow_key]
        
        # Check X-coordinate: elbow should be between shoulder and wrist or close to that line
        s_x, e_x, w_x = shoulder["x"], elbow["x"], wrist["x"]
        s_y, e_y, w_y = shoulder["y"], elbow["y"], wrist["y"]
        
        # Calculate angle between segments
        vec1 = (e_x - s_x, e_y - s_y)
        vec2 = (w_x - e_x, w_y - e_y)
        
        # Check for zero length vectors
        len_vec1 = (vec1[0]**2 + vec1[1]**2)**0.5
        len_vec2 = (vec2[0]**2 + vec2[1]**2)**0.5
        
        if len_vec1 > 0 and len_vec2 > 0:
            # Calculate dot product and normalize
            dot_product = (vec1[0] * vec2[0] + vec1[1] * vec2[1]) / (len_vec1 * len_vec2)
            angle = np.arccos(np.clip(dot_product, -1.0, 1.0)) * 180 / np.pi
            
            # Angle should not be too sharp (arm should be somewhat straight)
            if angle < 110:  # Allow some bend, but not too much
                return False
    
    # Calculate body height (rough estimate)
    body_height = 0
    if "left_shoulder" in keypoints and "left_ankle" in keypoints:
        shoulder_y = keypoints["left_shoulder"]["y"]
        ankle_y = keypoints["left_ankle"]["y"]
        body_height = max(body_height, ankle_y - shoulder_y)
    
    if "right_shoulder" in keypoints and "right_ankle" in keypoints:
        shoulder_y = keypoints["right_shoulder"]["y"]
        ankle_y = keypoints["right_ankle"]["y"]
        body_height = max(body_height, ankle_y - shoulder_y)
    
    # If we couldn't calculate body height, use a pixel-based approach as fallback
    if body_height <= 0:
        # Return True if wrist is significantly above shoulder (at least 50px)
        return (shoulder["y"] - wrist["y"]) > 50
    
    # Check if wrist is raised high enough above shoulder
    # height_threshold is the percentage of body height
    return (shoulder["y"] - wrist["y"]) > (height_threshold * body_height)

def get_person_bboxes(poses_list):
    """
    Calculate bounding boxes for all persons in pose list
    
    Args:
        poses_list: List of poses in format [x1,y1,v1,x2,y2,v2,...] 
    
    Returns:
        list: List of bounding boxes as [x1, y1, x2, y2]
    """
    bboxes = []
    
    for pose in poses_list:
        # Extract x,y coordinates from pose
        points_x = []
        points_y = []
        
        for i in range(0, len(pose), 3):
            if i+2 < len(pose) and pose[i+2] > 0.1:  # Visibility threshold
                points_x.append(pose[i])
                points_y.append(pose[i+1])
        
        if points_x and points_y:
            # Calculate bounding box with some padding
            x1 = max(0, int(min(points_x)) - 20)
            y1 = max(0, int(min(points_y)) - 20)
            x2 = int(max(points_x)) + 20
            y2 = int(max(points_y)) + 20
            
            bboxes.append([x1, y1, x2, y2])
        else:
            # Fallback empty box
            bboxes.append([0, 0, 10, 10])
    
    return bboxes

def draw_bboxes(image, bboxes, alert_indices, color=(0, 0, 255)):
    """
    Draw bounding boxes for specific person indices
    
    Args:
        image: OpenCV image
        bboxes: List of bounding boxes
        alert_indices: List of indices to draw
        color: Color as (B,G,R) tuple
        
    Returns:
        image: Image with boxes drawn
    """
    result_image = image.copy()
    
    for i in alert_indices:
        if 0 <= i < len(bboxes):
            x1, y1, x2, y2 = bboxes[i]
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(result_image, "Hands Up", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    
    return result_image
    len1 = (vec1[0]**2 + vec1[1]**2)**0.5
    len2 = (vec2[0]**2 + vec2[1]**2)**0.5
    
    if len1 < 1 or len2 < 1:
        return False
    
    # Normalize vectors
    vec1 = (vec1[0]/len1, vec1[1]/len1)
    vec2 = (vec2[0]/len2, vec2[1]/len2)
    
    # Dot product gives cosine of angle
    dot_product = vec1[0]*vec2[0] + vec1[1]*vec2[1]
    
    # Arm should not bend back on itself - reject sharp angles
    # Allow angles up to ~135 degrees (dot product around -0.7)
    return dot_product > -0.7

def filter_overlapping_detections(poses_list, indices):
    """Filter out overlapping or duplicate detections"""
    if not indices:
        return indices
        
    # Convert poses to bounding boxes
    bboxes = get_person_bboxes(poses_list)
    
    # Only include boxes for the alert indices
    filtered_indices = []
    for i in indices:
        duplicate = False
        
        # If bbox is invalid, skip
        if i >= len(bboxes) or (bboxes[i][0] == 0 and bboxes[i][1] == 0 and 
                               bboxes[i][2] <= 10 and bboxes[i][3] <= 10):
            continue
            
        # Check if this bbox overlaps significantly with any already included bbox
        for j in filtered_indices:
            if calculate_iou(bboxes[i], bboxes[j]) > 0.7:  # 70% overlap threshold
                duplicate = True
                break
        
        if not duplicate:
            filtered_indices.append(i)
            
    return filtered_indices

def calculate_iou(box1, box2):
    """Calculate Intersection over Union for two boxes"""
    # Box format is [x1, y1, x2, y2]
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    # Calculate intersection area
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    # Calculate union area
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = box1_area + box2_area - intersection
    
    # Return IoU
    return intersection / max(union, 1)

def get_keypoint_name(index):
    """Get the name of a COCO keypoint by index"""
    keypoint_names = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    if 0 <= index < len(keypoint_names):
        return keypoint_names[index]
    return f"unknown_{index}"

def is_keypoint_visible(x, y, visibility_score, threshold=0.1):
    """
    Check if a keypoint is visible and valid
    
    Args:
        x, y: Coordinates
        visibility_score: Confidence/visibility score
        threshold: Minimum score to consider visible
        
    Returns:
        bool: True if visible
    """
    # Check if coordinates are valid (non-zero)
    if x == 0 and y == 0:
        return False
        
    # Check if visibility score meets threshold
    if visibility_score < threshold:
        return False
        
    return True

def get_person_bboxes(poses_list):
    """
    Convert poses to bounding boxes around each person
    
    Args:
        poses_list: List of poses in format [x1,y1,v1,x2,y2,v2,...]
        
    Returns:
        list: List of bounding boxes in format [x1, y1, x2, y2]
    """
    bboxes = []
    
    for pose in poses_list:
        # Extract x, y coordinates
        x_coords = []
        y_coords = []
        
        for j in range(0, min(51, len(pose)), 3):
            x, y = pose[j], pose[j+1]
            if x > 0 and y > 0:
                x_coords.append(x)
                y_coords.append(y)
        
        # Create bbox if enough points
        if len(x_coords) >= 5 and len(y_coords) >= 5:
            # Add some padding around the person
            padding_x = (max(x_coords) - min(x_coords)) * 0.1
            padding_y = (max(y_coords) - min(y_coords)) * 0.1
            
            x1 = max(0, min(x_coords) - padding_x)
            y1 = max(0, min(y_coords) - padding_y)
            x2 = max(x_coords) + padding_x
            y2 = max(y_coords) + padding_y
            
            bboxes.append([x1, y1, x2, y2])
        else:
            # Invalid pose, add dummy bbox
            bboxes.append([0, 0, 10, 10])
    
    return bboxes

def draw_bboxes(image, bboxes, indices=None, color=(0, 0, 255), thickness=2, label_prefix="Person"):
    """
    Draw bounding boxes on image for persons with hands up
    
    Args:
        image: OpenCV image
        bboxes: List of bounding boxes [x1, y1, x2, y2]
        indices: Indices of bboxes to draw (for highlighting specific people)
        color: Color for the bounding box (B, G, R)
        thickness: Line thickness
        label_prefix: Prefix for the label text
        
    Returns:
        image: Image with boxes drawn
    """
    result_image = image.copy()
    
    # If no indices provided, draw all boxes
    if indices is None:
        indices = list(range(len(bboxes)))
    
    for i in indices:
        if i >= len(bboxes):
            continue
            
        bbox = bboxes[i]
        if len(bbox) != 4:
            continue
            
        x1, y1, x2, y2 = map(int, bbox)
        
        # Skip invalid boxes
        if x1 >= x2 or y1 >= y2 or x1 < 0 or y1 < 0 or x2 <= 10 or y2 <= 10:
            continue
            
        # Draw rectangle
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
        
        # Add label
        label = f"{label_prefix} {i}"
        cv2.putText(result_image, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)
    
    return result_image
