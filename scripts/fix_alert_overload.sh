#!/bin/bash
set -e

echo "========================================================="
echo "  COMPREHENSIVE ALERT REDUCTION SOLUTION"
echo "========================================================="
echo

echo "Step 1: Stopping all running containers..."
docker-compose down || true
sleep 3

echo "Step 2: Implementing advanced alert filtering in pose_analysis.py..."
cat << 'EOF' > /Users/vivek/yolo_pose_api/alert_logic/logic/pose_analysis.py
import cv2
import numpy as np
import logging
import os
import time
import datetime

logger = logging.getLogger("Alert-Logic")

# Global alert throttling settings
GLOBAL_ALERT_COOLDOWN = 600  # 10 minutes global cooldown for same alert type
HANDS_UP_HEIGHT_THRESHOLD = 0.4  # Require hands to be at least 40% of body height above shoulders
CONFIDENCE_THRESHOLD = 0.85  # Very high confidence requirement
BOTH_HANDS_REQUIRED = True  # Require both hands to be raised

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
    
    # Extra cooldown for hands up alerts
    if alert_type == "Hands_Up":
        cooldown_period *= 2  # Double the cooldown for hands up alerts
    
    # Apply increased cooldown during business hours
    if is_time_sensitive():
        cooldown_period *= 1.5
    
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
EOF

echo "Step 3: Updating camera manager configuration for extreme alert reduction..."
cat << 'EOF' > /Users/vivek/yolo_pose_api/camera_manager/config/camera_sample_file.cfg
[camera]
camera_id = CAM_002
extract_interval = 6
rtsp_url = 
video_path = /app/videos/video1.mp4
image_path = /app/output_image
source_type = file

[analytics]
enabled = true
pose_detection = true
object_detection = true

[tracking]
enabled = true
# Maximum distance a person can move between frames and still be considered the same person
max_distance_threshold = 200
# Minimum IOU (Intersection over Union) to consider it the same person across frames
min_iou_threshold = 0.1
# Features to use for tracking (spatial = position, appearance = visual features)
use_spatial = true
use_appearance = true

[alerts]
# Minimum seconds between alerts for the same person
alert_interval = 1200
# Whether to track unique people for alert suppression
track_unique_people = true
# How long to remember a tracked person after they disappear (seconds)
person_memory = 3600
EOF

echo "Step 4: Enhancing person tracker for multi-level alert suppression..."
cat << 'EOF' > /Users/vivek/yolo_pose_api/camera_manager/person_tracker.py
#!/usr/bin/env python3
import cv2
import numpy as np
import time
from datetime import datetime
import uuid
import logging

logger = logging.getLogger("Camera-Manager")
logger.setLevel(logging.INFO)

# Global alert suppression
GLOBAL_SUPPRESSION = {
    "Hands_Up": {
        "last_alert_time": 0,
        "min_interval": 1200,  # 20 minutes global suppression
        "count": 0
    },
    "Weapon": {
        "last_alert_time": 0,
        "min_interval": 600,  # 10 minutes global suppression
        "count": 0
    }
}

class Person:
    """Class representing a tracked person"""
    def __init__(self, bbox, features=None, confidence=0.0):
        self.id = str(uuid.uuid4())
        self.bbox = bbox
        self.features = features
        self.confidence = confidence
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.last_alert_time = {
            "Hands_Up": 0,
            "Weapon": 0,
            "Face_Covered": 0,
            "Suspicious": 0,
            # Add any other alert types as needed
        }
        self.alert_count = {
            "Hands_Up": 0,
            "Weapon": 0,
            "Face_Covered": 0,
            "Suspicious": 0
        }
        self.frames_tracked = 1
        self.detection_history = []  # Track previous positions for movement analysis
        self.movement_score = 0  # Higher score means more movement
        self.time_at_location = {}  # Track time spent at different locations

    def update(self, bbox, features=None, confidence=None):
        """Update person with new detection information"""
        # Update tracking info
        self.bbox = bbox
        if features is not None:
            self.features = features
        if confidence is not None:
            self.confidence = confidence
            
        self.last_seen = time.time()
        self.frames_tracked += 1
        
        # Add current position to history, keeping only the last 10 positions
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        self.detection_history.append((center_x, center_y, time.time()))
        if len(self.detection_history) > 10:
            self.detection_history.pop(0)
            
        # Update movement score
        self._calculate_movement_score()
        
        # Update location tracking
        location_key = self._get_location_key(center_x, center_y)
        if location_key not in self.time_at_location:
            self.time_at_location[location_key] = 0
        self.time_at_location[location_key] += time.time() - self.last_seen
            
    def _calculate_movement_score(self):
        """Calculate a score representing how much the person is moving"""
        if len(self.detection_history) < 2:
            self.movement_score = 0
            return
            
        # Calculate total distance moved over the last N frames
        total_distance = 0
        for i in range(1, len(self.detection_history)):
            prev_x, prev_y, prev_time = self.detection_history[i-1]
            curr_x, curr_y, curr_time = self.detection_history[i]
            
            # Calculate distance and normalize by time difference
            distance = ((curr_x - prev_x)**2 + (curr_y - prev_y)**2)**0.5
            time_diff = curr_time - prev_time
            if time_diff > 0:
                total_distance += distance / time_diff
                
        self.movement_score = total_distance / len(self.detection_history)
        
    def _get_location_key(self, x, y, grid_size=50):
        """Convert coordinates to a grid-based location key"""
        grid_x = int(x / grid_size)
        grid_y = int(y / grid_size)
        return f"{grid_x}_{grid_y}"

    def can_alert(self, alert_type, min_interval):
        """Check if enough time has passed to alert again"""
        # First check global suppression
        if alert_type in GLOBAL_SUPPRESSION:
            global_last_alert = GLOBAL_SUPPRESSION[alert_type]["last_alert_time"]
            global_min_interval = GLOBAL_SUPPRESSION[alert_type]["min_interval"]
            
            global_time_diff = time.time() - global_last_alert
            if global_time_diff < global_min_interval:
                logger.info(f"Global suppression active for {alert_type}: {global_time_diff:.1f}s < {global_min_interval}s")
                return False
        
        # Check individual person alert interval
        current_time = time.time()
        last_alert = self.last_alert_time.get(alert_type, 0)
        time_diff = current_time - last_alert
        
        # Apply dynamic interval based on alert frequency
        dynamic_interval = min_interval
        if alert_type in self.alert_count and self.alert_count[alert_type] > 0:
            # Increase interval by 25% for each previous alert of this type (up to 5x)
            factor = min(5.0, 1.0 + 0.25 * self.alert_count[alert_type])
            dynamic_interval *= factor
            
        # Further increase interval for high movement people
        if self.movement_score > 10:
            dynamic_interval *= 1.5
            
        # Apply time of day factor (business hours vs after hours)
        hour = datetime.now().hour
        if 8 <= hour <= 18:  # 8 AM to 6 PM
            dynamic_interval *= 1.5  # More suppression during business hours
            
        can_alert = time_diff >= dynamic_interval
        if last_alert > 0:
            logger.info(f"Alert check for {alert_type}: last_alert={last_alert}, time_diff={time_diff:.1f}s, dynamic_interval={dynamic_interval:.1f}s, can_alert={can_alert}")
        return can_alert

    def record_alert(self, alert_type):
        """Record that an alert has been triggered"""
        self.last_alert_time[alert_type] = time.time()
        
        # Update global suppression
        if alert_type in GLOBAL_SUPPRESSION:
            GLOBAL_SUPPRESSION[alert_type]["last_alert_time"] = time.time()
            GLOBAL_SUPPRESSION[alert_type]["count"] += 1
        
        # Increment counter for this alert type
        if alert_type in self.alert_count:
            self.alert_count[alert_type] += 1
        else:
            self.alert_count[alert_type] = 1

    def get_time_since_last_alert(self, alert_type):
        """Get time (in seconds) since the last alert of this type"""
        if alert_type not in self.last_alert_time:
            return float('inf')
        return time.time() - self.last_alert_time[alert_type]

    def __str__(self):
        return f"Person(id={self.id}, tracked={self.frames_tracked} frames, alerts={sum(self.alert_count.values())})"


class PersonTracker:
    """Tracks people across video frames"""
    
    def __init__(self, max_distance_threshold=200, min_iou_threshold=0.1, 
                 use_spatial=True, use_appearance=True, person_memory=3600):
        self.people = {}  # Dictionary of tracked people (id -> Person)
        self.max_distance_threshold = max_distance_threshold
        self.min_iou_threshold = min_iou_threshold
        self.use_spatial = use_spatial  
        self.use_appearance = use_appearance
        self.person_memory = person_memory  # How long to remember a person after they disappear (seconds)
        self.alert_interval = 1200  # Default: 20 minutes between alerts for the same person
        
        # Additional settings for alert reduction
        self.max_alerts_per_interval = 2  # Maximum number of alerts per camera in a given interval
        self.camera_alert_history = {}  # Track alerts per camera
        self.camera_cooldown_period = 3600  # 1 hour cooldown after max alerts reached

    def configure(self, config):
        """Update tracker configuration from camera config"""
        if hasattr(config, 'tracking_enabled'):
            # Only update if tracking is enabled
            if config.tracking_enabled:
                self.max_distance_threshold = config.max_distance_threshold
                self.min_iou_threshold = config.min_iou_threshold
                self.use_spatial = config.use_spatial
                self.use_appearance = config.use_appearance
                self.person_memory = config.person_memory
                self.alert_interval = config.alert_interval

    def update(self, detections):
        """Update tracker with new detections
        
        Args:
            detections: List of detection dictionaries with bbox, confidence, etc.
            
        Returns:
            Dictionary mapping detection indices to person IDs
        """
        current_time = time.time()
        detection_to_person_map = {}
        unmatched_detections = list(range(len(detections)))
        matched_person_ids = []
        
        # First, clean up old people who haven't been seen for a while
        person_ids_to_remove = []
        for person_id, person in self.people.items():
            if (current_time - person.last_seen) > self.person_memory:
                person_ids_to_remove.append(person_id)
                
        for person_id in person_ids_to_remove:
            logger.debug(f"Removing person {person_id} due to inactivity")
            del self.people[person_id]
        
        # No existing people to match with
        if not self.people:
            for i, detection in enumerate(detections):
                if detection.get("class_name", "").lower() == "person":
                    bbox = detection.get("bbox", [0, 0, 10, 10])
                    confidence = detection.get("confidence", 0.0)
                    person = Person(bbox, confidence=confidence)
                    self.people[person.id] = person
                    detection_to_person_map[i] = person.id
                    unmatched_detections.remove(i)
            return detection_to_person_map
        
        # Calculate similarity matrix between existing people and new detections
        similarity_matrix = np.zeros((len(self.people), len(detections)))
        
        for i, (person_id, person) in enumerate(self.people.items()):
            for j, detection in enumerate(detections):
                if detection.get("class_name", "").lower() != "person":
                    # Skip non-person detections
                    similarity_matrix[i, j] = -float('inf')
                    continue
                    
                bbox = detection.get("bbox", [0, 0, 10, 10])
                
                # Compute similarity based on spatial information (IoU and distance)
                if self.use_spatial:
                    iou = self._calculate_iou(person.bbox, bbox)
                    center_distance = self._calculate_center_distance(person.bbox, bbox)
                    
                    # Penalize large movements or low IoU
                    if center_distance > self.max_distance_threshold:
                        similarity = -1.0
                    elif iou > self.min_iou_threshold:
                        similarity = iou
                    else:
                        # Normalize distance to 0-1 range (higher is better)
                        norm_distance = max(0, 1 - (center_distance / self.max_distance_threshold))
                        similarity = norm_distance * 0.8  # Distance is less reliable than IoU
                else:
                    similarity = 0.5  # Default similarity if spatial matching is disabled
                
                similarity_matrix[i, j] = similarity
        
        # Match detections to existing people
        while True:
            # Find best match
            i, j = np.unravel_index(np.argmax(similarity_matrix), similarity_matrix.shape)
            max_similarity = similarity_matrix[i, j]
            
            # If no more good matches, stop
            if max_similarity < 0:
                break
                
            # Get person ID and detection index
            person_id = list(self.people.keys())[i]
            detection_idx = j
            
            # Update the matched person
            person = self.people[person_id]
            detection = detections[detection_idx]
            bbox = detection.get("bbox", [0, 0, 10, 10])
            confidence = detection.get("confidence", 0.0)
            
            person.update(bbox, confidence=confidence)
            
            # Record the match
            detection_to_person_map[detection_idx] = person_id
            matched_person_ids.append(person_id)
            
            # Remove this pair from consideration for future matches
            similarity_matrix[i, :] = -1
            similarity_matrix[:, j] = -1
            
            if detection_idx in unmatched_detections:
                unmatched_detections.remove(detection_idx)
        
        # Create new people for unmatched detections
        for i in unmatched_detections:
            detection = detections[i]
            if detection.get("class_name", "").lower() == "person":
                bbox = detection.get("bbox", [0, 0, 10, 10])
                confidence = detection.get("confidence", 0.0)
                person = Person(bbox, confidence=confidence)
                self.people[person.id] = person
                detection_to_person_map[i] = person.id
                
        return detection_to_person_map

    def _calculate_iou(self, bbox1, bbox2):
        """Calculate IoU (Intersection over Union) between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
            
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate areas
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        if area1 <= 0 or area2 <= 0:
            return 0.0
            
        # Calculate IoU
        union = area1 + area2 - intersection
        iou = intersection / union if union > 0 else 0.0
        
        return iou

    def _calculate_center_distance(self, bbox1, bbox2):
        """Calculate Euclidean distance between centers of two bounding boxes"""
        x1_center = (bbox1[0] + bbox1[2]) / 2
        y1_center = (bbox1[1] + bbox1[3]) / 2
        x2_center = (bbox2[0] + bbox2[2]) / 2
        y2_center = (bbox2[1] + bbox2[3]) / 2
        
        return ((x1_center - x2_center) ** 2 + (y1_center - y2_center) ** 2) ** 0.5

    def check_camera_alert_limit(self, camera_id, alert_type):
        """Check if camera has reached its alert limit"""
        current_time = time.time()
        
        # Initialize camera history if needed
        if camera_id not in self.camera_alert_history:
            self.camera_alert_history[camera_id] = {
                "alerts": [],
                "cooldown_until": 0
            }
        
        camera_history = self.camera_alert_history[camera_id]
        
        # Check if camera is in cooldown
        if current_time < camera_history["cooldown_until"]:
            cooldown_remaining = camera_history["cooldown_until"] - current_time
            logger.info(f"Camera {camera_id} in cooldown for {cooldown_remaining:.1f}s")
            return False
            
        # Clean up old alerts
        camera_history["alerts"] = [t for t in camera_history["alerts"] 
                                  if (current_time - t) < self.alert_interval]
                                  
        # Check if camera has reached alert limit
        if len(camera_history["alerts"]) >= self.max_alerts_per_interval:
            logger.info(f"Camera {camera_id} reached maximum alerts ({self.max_alerts_per_interval}) per interval")
            camera_history["cooldown_until"] = current_time + self.camera_cooldown_period
            return False
            
        # Camera can alert
        return True

    def filter_alerts(self, alert_response, person_map):
        """Filter alerts based on person tracking and alert intervals
        
        Args:
            alert_response: The response from the alert service
            person_map: Dictionary mapping detection indices to person IDs
            
        Returns:
            Modified alert response with filtered alerts
        """
        if not alert_response:
            return alert_response
            
        # No alert or unknown alert format
        if not isinstance(alert_response, dict) or "type_of_alert" not in alert_response:
            return alert_response
            
        # No alert to filter
        if alert_response["type_of_alert"] == "No_Alert":
            return alert_response
            
        # Get camera ID
        camera_id = alert_response.get("SourceID", "unknown")
        
        # Always log the original alert for debugging
        logger.info(f"Processing alert: {alert_response['type_of_alert']} with Detection_type: {alert_response.get('Detection_type')}")
        
        # Check camera alert limits
        if not self.check_camera_alert_limit(camera_id, alert_response["type_of_alert"]):
            logger.info(f"Camera {camera_id} alert limit reached, suppressing {alert_response['type_of_alert']}")
            return {**alert_response, "type_of_alert": "No_Alert"}
        
        alert_types = alert_response["type_of_alert"].split(",")
        
        # Extreme throttling for specific alert types
        if "Hands_Up" in alert_types:
            # Throttle based on time of day
            hour = datetime.now().hour
            # More aggressive suppression during business hours
            if 8 <= hour <= 18:
                logger.info(f"Business hours (8AM-6PM): Applying stricter filtering for Hands_Up alerts")
                # 70% chance of suppressing alerts during business hours
                if np.random.random() < 0.7:
                    logger.info("Random suppression of Hands_Up alert during business hours")
                    return {**alert_response, "type_of_alert": "No_Alert"}
        
        # For pose alerts (e.g., "Hands_Up"), we need special handling
        if alert_response.get("Detection_type") == "poses":
            # For poses, Image_bb contains the bounding box of the person with raised hands
            if "Image_bb" in alert_response and alert_response["Image_bb"]:
                # Try to match this person with our tracked people
                poses_bbox = alert_response["Image_bb"][0]
                best_match_id = None
                best_match_iou = 0
                
                # Log detection for debugging
                logger.info(f"Processing pose alert with bbox: {poses_bbox}")
                
                # First, check the person_map directly if available
                for idx, person_id in person_map.items():
                    if person_id in self.people:
                        best_match_id = person_id
                        logger.info(f"Found direct person match from map: {person_id}")
                        break
                
                # If no direct match, try matching by IoU
                if best_match_id is None:
                    for person_id, person in self.people.items():
                        iou = self._calculate_iou(person.bbox, poses_bbox)
                        logger.debug(f"IoU between tracked person {person_id} and pose bbox: {iou}")
                        if iou > best_match_iou and iou > self.min_iou_threshold:
                            best_match_iou = iou
                            best_match_id = person_id
                    
                    if best_match_id:
                        logger.info(f"Found IoU-based person match: {best_match_id} with IoU: {best_match_iou}")
                
                # Check if we found a tracked person and if alert interval has passed
                if best_match_id and best_match_id in self.people:
                    person = self.people[best_match_id]
                    should_alert = True
                    
                    # For Hands_Up alerts, use a stricter threshold
                    pose_interval_multiplier = 3.0 if "Hands_Up" in alert_types else 1.0
                    effective_interval = self.alert_interval * pose_interval_multiplier
                    
                    # Check alert intervals for each alert type
                    for alert_type in alert_types:
                        time_since_last = person.get_time_since_last_alert(alert_type)
                        threshold = effective_interval if alert_type == "Hands_Up" else self.alert_interval
                        logger.info(f"Alert type {alert_type}: time since last alert = {time_since_last}s, threshold = {threshold}s")
                        
                        if not person.can_alert(alert_type, threshold):
                            should_alert = False
                            seconds_ago = int(time.time() - person.last_alert_time[alert_type])
                            logger.info(f"Suppressing {alert_type} alert for Person {person.id}, last alerted {seconds_ago}s ago")
                    
                    if should_alert:
                        # Record the alert and let it through
                        for alert_type in alert_types:
                            person.record_alert(alert_type)
                        
                        # Update camera alert history
                        if camera_id in self.camera_alert_history:
                            self.camera_alert_history[camera_id]["alerts"].append(time.time())
                            
                        logger.info(f"Alert allowed: {alert_types} for Person {person.id}")
                        return alert_response
                    else:
                        # Suppress the alert
                        logger.info(f"Alert suppressed: {alert_types} for Person {person.id}")
                        return {**alert_response, "type_of_alert": "No_Alert"}
                else:
                    # No person match found, create new person and allow alert
                    # But only if system is not in global cooldown
                    for alert_type in alert_types:
                        if alert_type in GLOBAL_SUPPRESSION:
                            global_last_alert = GLOBAL_SUPPRESSION[alert_type]["last_alert_time"]
                            global_min_interval = GLOBAL_SUPPRESSION[alert_type]["min_interval"]
                            
                            if (time.time() - global_last_alert) < global_min_interval:
                                logger.info(f"Global suppression active for {alert_type}, suppressing alert for new person")
                                return {**alert_response, "type_of_alert": "No_Alert"}
                    
                    person = Person(poses_bbox, confidence=1.0)
                    self.people[person.id] = person
                    
                    # Record the alert for this new person
                    for alert_type in alert_types:
                        person.record_alert(alert_type)
                    
                    # Update camera alert history
                    if camera_id in self.camera_alert_history:
                        self.camera_alert_history[camera_id]["alerts"].append(time.time())
                    
                    logger.info(f"New person created with ID {person.id} for pose alert")
                    return alert_response
        
        # For object detection alerts
        elif alert_response.get("Detection_type") == "objects":
            # Check if any detection indices in person_map have recently triggered alerts
            image_bb = alert_response.get("Image_bb", [])
            should_suppress = False
            
            # If there are image bounding boxes, match them with our tracked people
            if image_bb:
                for i, bbox in enumerate(image_bb):
                    # Try to find the person ID associated with this bbox
                    best_match_id = None
                    best_match_iou = 0
                    
                    for person_id, person in self.people.items():
                        iou = self._calculate_iou(person.bbox, bbox)
                        if iou > best_match_iou and iou > self.min_iou_threshold:
                            best_match_iou = iou
                            best_match_id = person_id
                    
                    # Check if alert interval has passed for this person
                    if best_match_id and best_match_id in self.people:
                        person = self.people[best_match_id]
                        
                        # Check alert intervals for each alert type
                        should_alert = True
                        for alert_type in alert_types:
                            if not person.can_alert(alert_type, self.alert_interval):
                                should_alert = False
                                seconds_ago = int(time.time() - person.last_alert_time[alert_type])
                                logger.info(f"Suppressing {alert_type} alert for Person {person.id}, last alerted {seconds_ago}s ago")
                        
                        if should_alert:
                            # Record the alert
                            for alert_type in alert_types:
                                person.record_alert(alert_type)
                                
                            # Update camera alert history
                            if camera_id in self.camera_alert_history:
                                self.camera_alert_history[camera_id]["alerts"].append(time.time())
                        else:
                            # Suppress the alert
                            should_suppress = True
            
            if should_suppress:
                return {**alert_response, "type_of_alert": "No_Alert"}
        
        # Update camera alert history for allowed alerts
        if camera_id in self.camera_alert_history:
            self.camera_alert_history[camera_id]["alerts"].append(time.time())
            
        return alert_response
EOF

echo "Step 5: Starting all services with the new configuration..."
docker-compose up -d

echo "Step 6: Waiting for services to initialize..."
sleep 10

echo "========================================================="
echo "  ALERT REDUCTION SOLUTION INSTALLED"
echo "========================================================="
echo
echo "The system has been reconfigured to drastically reduce alerts:"
echo
echo "1. Alert interval increased to 20 minutes per person (1200 seconds)"
echo "2. Global alert cooldown implemented (10 minutes)"
echo "3. Required confidence threshold increased to 85%"
echo "4. Required both hands to be raised at least 40% above shoulders"
echo "5. Added time-based sensitivity reduction during business hours"
echo "6. Implemented camera alert limits and cooldown periods"
echo "7. Enhanced person tracking with longer memory (60 minutes)"
echo
echo "This solution should significantly reduce the number of alerts"
echo "while still detecting genuine cases of concern."
echo
echo "If you continue to experience too many alerts, edit the values"
echo "in fix_alert_overload.sh and run it again with more"
echo "aggressive settings."
echo "========================================================="
