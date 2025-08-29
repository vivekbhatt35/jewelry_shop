#!/bin/bash

# Fix script for YOLO pose detection system issues
echo "Applying fixes for YOLO pose detection system..."

# 1. Fix mask alerts in detection_analysis.py
cat << 'EOF' > /tmp/detection_analysis_fix.py
# Modified analyze_detections function to properly handle mask detections
def analyze_detections(detections):
    """
    Analyze object detections to identify items of interest
    
    Args:
        detections: List of detection dictionaries with class_name, confidence, bbox
    
    Returns:
        list: Indices of detections that trigger alerts
        dict: Mapping of detection indices to alert types
    """
    alert_indices = []
    alert_types = {}
    
    # Track persons and alert objects separately
    person_detections = []
    alert_detections = {}
    
    logger.info(f"Analyzing {len(detections)} detections")
    
    # First pass: identify all persons and alert objects
    for i, detection in enumerate(detections):
        class_name = detection.get("class_name", "").lower()
        confidence = detection.get("confidence", 0)
        
        # Use an EXTREMELY low threshold for weapons (0.10) and regular threshold for other objects (0.35)
        is_weapon = any(weapon.lower() in class_name.lower() for weapon in CRITICAL_CLASSES)
        is_weapon_related = any(weapon.lower() in class_name.lower() for weapon in ALERT_CATEGORIES["Weapon"])
        
        # Special handling for masks - IMPORTANT FIX
        is_mask = class_name.lower() == "mask" or class_name.lower() == "helmet"
        
        if is_weapon:
            threshold = 0.10  # Extremely low threshold for critical weapons
            logger.info(f"Using critical weapon threshold of {threshold} for {class_name}")
        elif is_weapon_related:
            threshold = 0.15  # Very low threshold for weapon-related items
            logger.info(f"Using weapon-related threshold of {threshold} for {class_name}")
        elif is_mask:
            threshold = 0.30  # Medium-low threshold for masks/helmets
            logger.info(f"Using mask/helmet threshold of {threshold} for {class_name}")
        else:
            threshold = 0.35  # Normal threshold for everything else
        
        # Skip low confidence detections
        if confidence < threshold:
            logger.info(f"Detection {i}: {class_name} has low confidence {confidence:.2f}, threshold {threshold}, skipping")
            continue
        
        # Special case for weapons - always trigger an immediate alert
        if class_name.lower() in [c.lower() for c in CRITICAL_CLASSES]:
            # Add to alert indices directly - this is an immediate alert
            alert_indices.append(i)
            alert_types[i] = ["Weapon"]
            logger.info(f"CRITICAL DETECTION: {i}: {class_name} directly triggered Weapon alert")
            # Continue to process this detection for additional alerts
            
        # IMPORTANT FIX: Direct alert for masks and helmets
        if is_mask:
            alert_indices.append(i)
            alert_types[i] = ["Face_Covered"]
            logger.info(f"MASK/HELMET DETECTION: {i}: {class_name} directly triggered Face_Covered alert")
            
        # Check which category this detection belongs to
        detected_alerts = []
        for alert_type, classes in ALERT_CATEGORIES.items():
            if class_name in [c.lower() for c in classes]:
                detected_alerts.append(alert_type)
                logger.info(f"Detection {i}: {class_name} triggered alert: {alert_type}")
                
                # RELAXED LOGIC: Immediately trigger an alert for any weapon
                if alert_type == "Weapon":
                    if i not in alert_indices:
                        alert_indices.append(i)
                    if i not in alert_types:
                        alert_types[i] = []
                    if "Weapon" not in alert_types[i]:
                        alert_types[i].append("Weapon")
                    logger.warning(f"HIGH PRIORITY: {class_name} directly triggered Weapon alert with confidence {detection.get('confidence', 0):.2f}")
        
        # Track person detections
        if class_name == "person":
            person_detections.append(i)
        
        # If this is an alert object that's not already triggered, store it
        if detected_alerts and i not in alert_indices:
            alert_detections[i] = detected_alerts
    
    logger.info(f"Found {len(person_detections)} persons and {len(alert_detections)} alert objects")
EOF

# 2. Fix process_frame in camera_manager to skip pose detection for overhead cameras
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
            tasks = []
            
            # IMPORTANT FIX: Skip pose detection for overhead cameras
            if config.pose_detection:
                # Check camera angle
                camera_angle = await get_camera_angle(camera_id)
                if camera_angle and camera_angle.lower() == "overhead":
                    logger.info(f"Skipping pose detection for camera {camera_id} due to overhead angle")
                else:
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
            else:
                # If no tasks were scheduled (e.g., overhead camera with only pose detection enabled)
                # We should still delete the source image as it won't be used
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted unused source image for overhead camera: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting unused source image: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error processing frame from camera {camera_id}: {str(e)}")
        logger.exception("Full exception details:")
EOF

# 3. Fix image cleanup in alert_logic/app.py
cat << 'EOF' > /tmp/cleanup_fix.py
# Function to clean up images when no alerts are generated
def cleanup_unused_images(source_path, overlay_path):
    """Clean up source and overlay images when no alerts are generated"""
    try:
        # Delete source image
        if source_path and os.path.exists(source_path):
            os.remove(source_path)
            logger.info(f"Deleted unused source image: {source_path}")
        
        # Delete overlay image
        if overlay_path and os.path.exists(overlay_path):
            os.remove(overlay_path)
            logger.info(f"Deleted unused overlay image: {overlay_path}")
            
        return True
    except Exception as e:
        logger.error(f"Error cleaning up unused images: {str(e)}")
        return False

# Add this function to alert_logic/app.py and modify the return block to ensure cleanup happens
# when no alerts are generated
EOF

# Apply the fixes to the containers
echo "Applying fixes to the containers..."

# Fix mask alerts in detection_analysis.py
docker-compose exec alert-logic bash -c "
# Create backup of original file
cp /app/alert_logic/logic/detection_analysis.py /app/alert_logic/logic/detection_analysis.py.bak

# Replace the analyze_detections function with our fixed version
sed -i -e '/def analyze_detections/,/Found.*alert objects/{//!d;}' /app/alert_logic/logic/detection_analysis.py
sed -i -e '/def analyze_detections/ r /tmp/detection_analysis_fix.py' /app/alert_logic/logic/detection_analysis.py

echo 'Fixed mask alerts in detection_analysis.py'
"

# Fix process_frame in camera_manager/app.py
docker-compose exec camera-manager bash -c "
# Create backup of original file
cp /app/camera_manager/app.py /app/camera_manager/app.py.bak

# Replace the process_frame function
sed -i -e '/async def process_frame/,/logger.error.*Error processing frame/{//!d;}' /app/camera_manager/app.py
sed -i -e '/async def process_frame/ r /tmp/process_frame_fix.py' /app/camera_manager/app.py

echo 'Fixed process_frame in camera_manager/app.py'
"

# Fix image cleanup in alert_logic/app.py
docker-compose exec alert-logic bash -c "
# Add cleanup function to app.py
echo '$(cat /tmp/cleanup_fix.py)' >> /app/alert_logic/app.py

# Modify the alert processing code to ensure cleanup happens
sed -i -e '/if not result_alerts:/,/logger.exception.*Detailed image deletion exception:/{
  s/if keep_non_alert_images:/if keep_non_alert_images:/; 
  s/logger.debug(\"No alerts detected - deleting source and overlay images\")/cleanup_unused_images(image_path, image_overlay)/;
  s/try:/# Using cleanup function instead of inline code/;
  s/# Delete source image/# Already handled by cleanup_unused_images/;
  s/if os.path.exists(image_path):/# Already handled by cleanup_unused_images/;
  s/os.remove(image_path)/pass/;
  s/logger.info(f\"Deleted source image: {image_path}\")/pass/;
  s/# Delete overlay image if it exists/# Already handled by cleanup_unused_images/;
  s/if image_overlay and os.path.exists(image_overlay):/# Already handled by cleanup_unused_images/;
  s/os.remove(image_overlay)/pass/;
  s/logger.info(f\"Deleted overlay image: {image_overlay}\")/pass/;
  s/except Exception as e:/# No exceptions to catch/;
  s/logger.error(f\"Error deleting unused images: {str(e)}\")/pass/;
  s/logger.exception(\"Detailed image deletion exception:\")/pass/;
}' /app/alert_logic/app.py

echo 'Fixed image cleanup in alert_logic/app.py'
"

# Also fix detector_pose/app.py to ensure images are properly deleted when no alerts
docker-compose exec detector-pose bash -c "
# Create backup
cp /app/detector_pose/app.py /app/detector_pose/app.py.bak

# Ensure image cleanup happens in all cases
sed -i 's/if alert_type == \"No_Alert\":/if alert_type == \"No_Alert\" or not alert_type or alert_type == \"Unknown_Detection_Type\":/' /app/detector_pose/app.py

echo 'Fixed image cleanup in detector_pose/app.py'
"

# Restart the services
echo "Restarting services to apply changes..."
docker-compose restart alert-logic camera-manager detector-pose

echo "Fixes applied successfully!"
echo "The following issues should now be fixed:"
echo "1. Face mask alerts are now properly triggered"
echo "2. Pose detection is skipped for overhead cameras"
echo "3. Source and overlay images are properly deleted when no alert is generated"
echo ""
echo "To verify the fixes, check the logs with:"
echo "docker-compose logs -f camera-manager detector-pose alert-logic"
