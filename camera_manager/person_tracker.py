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
