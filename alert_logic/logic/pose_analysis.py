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

def hands_up_detect(poses_list):
    """
    Detect persons with hands up in poses list
    With improved validation for better accuracy
    
    Args:
        poses_list: List of poses in format [x1,y1,v1,x2,y2,v2,...] 
                   where each pose has 17 keypoints x 3 values (x,y,v)
    
    Returns:
        list: Indices of persons with hands up
    """
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
            if confidence_score < CONFIDENCE_THRESHOLD:  # Stricter threshold
                logger.info(f"Person {i}: Low confidence score ({confidence_score:.2f} < {CONFIDENCE_THRESHOLD}), skipping")
                continue
            
            # Get image dimensions from any valid point
            img_width, img_height = 1000, 1000  # Defaults
            for kp in keypoints.values():
                if kp.get("x", 0) > 0:
                    img_width = max(img_width, kp.get("x", 0) * 2)
                    img_height = max(img_height, kp.get("y", 0) * 2)
            
            # Check if any key parts are in blacklist regions
            nose = keypoints.get("nose", {})
            if nose and is_in_blacklist_region(nose.get("x", 0), nose.get("y", 0), img_width, img_height):
                logger.info(f"Person {i}: In blacklist region, skipping")
                continue
            
            # Get arm keypoints
            left_wrist = keypoints.get("left_wrist", {})
            right_wrist = keypoints.get("right_wrist", {})
            left_elbow = keypoints.get("left_elbow", {})
            right_elbow = keypoints.get("right_elbow", {})
            left_shoulder = keypoints.get("left_shoulder", {})
            right_shoulder = keypoints.get("right_shoulder", {})
            
            # Skip if any required part is missing
            left_arm_complete = (left_wrist.get("x", 0) > 0 and 
                               left_elbow.get("x", 0) > 0 and 
                               left_shoulder.get("x", 0) > 0)
            
            right_arm_complete = (right_wrist.get("x", 0) > 0 and 
                                right_elbow.get("x", 0) > 0 and 
                                right_shoulder.get("x", 0) > 0)
            
            # Calculate body dimensions
            all_x_coords = [kp.get("x", 0) for kp in keypoints.values() if kp.get("x", 0) > 0]
            all_y_coords = [kp.get("y", 0) for kp in keypoints.values() if kp.get("y", 0) > 0]
            
            if not all_x_coords or not all_y_coords:
                logger.info(f"Person {i}: Not enough valid keypoints")
                continue
                
            # Body dimensions
            pose_width = max(all_x_coords) - min(all_x_coords)
            pose_height = max(all_y_coords) - min(all_y_coords)
            body_ratio = pose_height / max(pose_width, 1)
            
            # Check arms alignment
            left_arm_aligned = check_arm_alignment(left_shoulder, left_elbow, left_wrist)
            right_arm_aligned = check_arm_alignment(right_shoulder, right_elbow, right_wrist)
            
            logger.info(f"Person {i}: Left arm aligned: {left_arm_aligned}, Right arm aligned: {right_arm_aligned}")
            
            # For hands up, we need:
            # 1. Wrists above shoulders
            # 2. Arms properly aligned (elbow between shoulder and wrist)
            # 3. Reasonable body proportions
            
            left_hand_up = False
            if left_arm_complete and left_arm_aligned:
                left_hand_up = left_wrist["y"] < left_shoulder["y"]
                # Calculate how high above shoulder
                shoulder_to_wrist_height = (left_shoulder["y"] - left_wrist["y"]) / max(pose_height, 1)
                logger.info(f"Person {i}: Left wrist {shoulder_to_wrist_height:.2f} of body height above shoulder")
                # Must meet height threshold
                left_hand_up = left_hand_up and shoulder_to_wrist_height > HANDS_UP_HEIGHT_THRESHOLD
            
            right_hand_up = False
            if right_arm_complete and right_arm_aligned:
                right_hand_up = right_wrist["y"] < right_shoulder["y"]
                # Calculate how high above shoulder
                shoulder_to_wrist_height = (right_shoulder["y"] - right_wrist["y"]) / max(pose_height, 1)
                logger.info(f"Person {i}: Right wrist {shoulder_to_wrist_height:.2f} of body height above shoulder")
                # Must meet height threshold
                right_hand_up = right_hand_up and shoulder_to_wrist_height > HANDS_UP_HEIGHT_THRESHOLD
            
            # Check if we need both hands up
            hands_up_condition = False
            if BOTH_HANDS_REQUIRED:
                hands_up_condition = left_hand_up and right_hand_up
            else:
                hands_up_condition = left_hand_up or right_hand_up
            
            # Only consider valid hands up if pose confidence is good
            if hands_up_condition and confidence_score >= CONFIDENCE_THRESHOLD:
                logger.info(f"Person {i}: Valid hands up detected!")
                alert_indices.append(i)
            else:
                logger.info(f"Person {i}: No valid hands up detected")
    
    # Filter any duplicate or overlapping detections
    alert_indices = filter_overlapping_detections(poses_list, alert_indices)
    
    logger.info(f"Found {len(alert_indices)} persons with hands up: {alert_indices}")
    return alert_indices

def calculate_pose_confidence(keypoints):
    """
    Calculate a confidence score for the pose based on keypoint presence and positions
    
    Args:
        keypoints: Dictionary of keypoints
        
    Returns:
        float: Confidence score between 0 and 1
    """
    # Check if key body parts are present
    core_parts = ["nose", "left_shoulder", "right_shoulder", "left_hip", "right_hip"]
    core_parts_present = sum(1 for part in core_parts if keypoints.get(part, {}).get("x", 0) > 0)
    
    # Check for arm parts
    arm_parts = ["left_elbow", "right_elbow", "left_wrist", "right_wrist"]
    arm_parts_present = sum(1 for part in arm_parts if keypoints.get(part, {}).get("x", 0) > 0)
    
    # Check for leg parts
    leg_parts = ["left_knee", "right_knee", "left_ankle", "right_ankle"]
    leg_parts_present = sum(1 for part in leg_parts if keypoints.get(part, {}).get("x", 0) > 0)
    
    # Check for face parts
    face_parts = ["left_eye", "right_eye", "left_ear", "right_ear"]
    face_parts_present = sum(1 for part in face_parts if keypoints.get(part, {}).get("x", 0) > 0)
    
    # Calculate symmetry (both sides of body should be roughly symmetric)
    has_symmetry = is_pose_symmetric(keypoints)
    
    # Weighted scores
    core_score = core_parts_present / len(core_parts) * 0.4  # 40% weight
    arm_score = arm_parts_present / len(arm_parts) * 0.3     # 30% weight
    leg_score = leg_parts_present / len(leg_parts) * 0.1     # 10% weight
    face_score = face_parts_present / len(face_parts) * 0.1  # 10% weight
    symmetry_score = 0.1 if has_symmetry else 0              # 10% weight
    
    total_score = core_score + arm_score + leg_score + face_score + symmetry_score
    return min(1.0, total_score)  # Cap at 1.0

def is_pose_symmetric(keypoints):
    """Check if pose has reasonable left/right symmetry"""
    # Check if left and right sides are roughly symmetric
    key_pairs = [
        ("left_shoulder", "right_shoulder"),
        ("left_hip", "right_hip"),
        ("left_knee", "right_knee"),
        ("left_ankle", "right_ankle")
    ]
    
    symmetric_pairs = 0
    for left_part, right_part in key_pairs:
        left = keypoints.get(left_part, {})
        right = keypoints.get(right_part, {})
        
        if left.get("x", 0) > 0 and right.get("x", 0) > 0:
            symmetric_pairs += 1
    
    # Consider symmetric if at least half the pairs are present
    return symmetric_pairs >= len(key_pairs) / 2

def check_arm_alignment(shoulder, elbow, wrist):
    """
    Check if arm joints are in anatomically reasonable alignment
    
    Returns:
        bool: True if alignment is reasonable
    """
    # Skip check if any part is missing
    if not (shoulder.get("x", 0) > 0 and elbow.get("x", 0) > 0 and wrist.get("x", 0) > 0):
        return False
    
    # Check X-coordinate: elbow should be between shoulder and wrist or close to that line
    s_x, e_x, w_x = shoulder["x"], elbow["x"], wrist["x"]
    s_y, e_y, w_y = shoulder["y"], elbow["y"], wrist["y"]
    
    # Calculate angle between segments
    vec1 = (e_x - s_x, e_y - s_y)
    vec2 = (w_x - e_x, w_y - e_y)
    
    # Check for zero length vectors
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
