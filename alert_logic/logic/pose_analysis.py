import cv2
import numpy as np
import logging
import os

logger = logging.getLogger("Alert-Logic")

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
            if confidence_score < 0.4:  # Threshold for reliable pose
                logger.info(f"Person {i}: Low confidence score, skipping")
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
                # Must be at least 10% of body height above shoulder
                left_hand_up = left_hand_up and shoulder_to_wrist_height > 0.1
            
            right_hand_up = False
            if right_arm_complete and right_arm_aligned:
                right_hand_up = right_wrist["y"] < right_shoulder["y"]
                # Calculate how high above shoulder
                shoulder_to_wrist_height = (right_shoulder["y"] - right_wrist["y"]) / max(pose_height, 1)
                logger.info(f"Person {i}: Right wrist {shoulder_to_wrist_height:.2f} of body height above shoulder")
                # Must be at least 10% of body height above shoulder
                right_hand_up = right_hand_up and shoulder_to_wrist_height > 0.1
            
            # Only consider valid hands up if pose confidence is good
            if (left_hand_up or right_hand_up) and confidence_score >= 0.6:
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
    Calculate bounding boxes for each person based on keypoints
    Handles zero visibility scores
    
    Args:
        poses_list: List of poses in flat format
    
    Returns:
        list: Bounding boxes as [x1, y1, x2, y2]
    """
    bboxes = []
    
    for pose in poses_list:
        # Extract coordinates (even with zero visibility)
        points = []
        for i in range(0, len(pose), 3):
            x, y = pose[i:i+2]
            if x > 0 and y > 0:  # Use only non-zero coordinates
                points.append((x, y))
        
        coords = np.array(points) if points else np.array([])
        
        if len(coords) > 2:  # Need at least a few points
            # Get min/max coordinates
            x_min = max(0, np.min(coords[:, 0]))
            y_min = max(0, np.min(coords[:, 1]))
            x_max = np.max(coords[:, 0])
            y_max = np.max(coords[:, 1])
            
            # Add padding
            width = x_max - x_min
            height = y_max - y_min
            padding_x = width * 0.1
            padding_y = height * 0.1
            
            x_min = max(0, x_min - padding_x)
            y_min = max(0, y_min - padding_y)
            x_max += padding_x
            y_max += padding_y
            
            bboxes.append([int(x_min), int(y_min), int(x_max), int(y_max)])
        else:
            bboxes.append([0, 0, 10, 10])  # Small default box
    
    return bboxes

def draw_bboxes(image, bboxes, indices=None, color=(0, 0, 255), thickness=2):
    """Draw bounding boxes on image"""
    result_image = image.copy()
    
    if indices is None:
        indices = range(len(bboxes))
    
    for idx in indices:
        if idx < len(bboxes):
            x1, y1, x2, y2 = bboxes[idx]
            
            # Skip invalid boxes
            if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
                continue
                
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
            
            # Add text above the box
            cv2.putText(result_image, "HANDS UP", (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return result_image
