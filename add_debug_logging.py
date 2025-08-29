#!/usr/bin/env python3
"""
Script to fix camera_manager app.py with improved debugging for pose detection
"""

import os
import sys
import re

def add_debug_logging():
    """Add debug logging to help diagnose pose detection issues"""
    file_path = os.path.join('camera_manager', 'app.py')
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add debug logging to process_frame
    process_frame_regex = r"async def process_frame\(camera_id, frame, config\):"
    process_frame_debug = """async def process_frame(camera_id, frame, config):
    \"\"\"Process a video frame according to analytics settings\"\"\"
    try:
        # Debug logging for configuration
        logger.debug(f"Processing frame for camera {camera_id} with config: analytics_enabled={config.analytics_enabled}, "
                    f"pose_detection={config.pose_detection}, object_detection={config.object_detection}, "
                    f"tracking_enabled={config.tracking_enabled if hasattr(config, 'tracking_enabled') else False}, "
                    f"track_unique_people={config.track_unique_people if hasattr(config, 'track_unique_people') else False}")"""
    
    content = re.sub(process_frame_regex, process_frame_debug, content)
    
    # Add explicit log for skipping pose detection
    tracking_check_regex = r"# When tracking is disabled, process normally"
    tracking_check_debug = """# When tracking is disabled, process normally
                logger.debug(f"Running with tracking disabled. Pose detection enabled: {config.pose_detection}")"""
    
    content = re.sub(tracking_check_regex, tracking_check_debug, content)
    
    # Add better error handling for pose detection service
    pose_service_regex = r"async def send_to_pose_service\(camera_id, image_path, timestamp\):"
    pose_service_debug = """async def send_to_pose_service(camera_id, image_path, timestamp):
    \"\"\"Send image to pose detection service\"\"\"
    try:
        # Add detailed logging
        logger.info(f"Sending frame to pose service for camera {camera_id}")"""
    
    content = re.sub(pose_service_regex, pose_service_debug, content)
    
    # Fix camera config parsing to ensure pose_detection is properly set
    config_parsing_regex = r"config\.pose_detection = analytics_section\.getboolean\('pose_detection', False\)"
    config_parsing_fix = """config.pose_detection = analytics_section.getboolean('pose_detection', False)
            logger.info(f"Camera {camera_id} pose_detection set to: {config.pose_detection}")"""
    
    content = re.sub(config_parsing_regex, config_parsing_fix, content)
    
    # Add special debug logging for when pose_detection is enabled but not being called
    tasks_append_regex = r"if config\.pose_detection:"
    tasks_append_debug = """if config.pose_detection:
                    logger.info(f"Adding pose detection task for camera {camera_id}")"""
    
    content = re.sub(tasks_append_regex, tasks_append_debug, content)
    
    # Add error handling for potentially corrupted config
    if "camera_trackers.get_value()" in content:
        corrupted_config_fix = re.sub(r"camera_trackers\.get_value\(\)", "camera_trackers.get(camera_id)", content)
        content = corrupted_config_fix
    
    # Write the modified content back to the file
    backup_path = file_path + '.backup'
    print(f"Creating backup of original file at {backup_path}")
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"Backup created at {backup_path}")
    print("To apply the changes, run:")
    print(f"cp {backup_path} {file_path}")
    
    # Create a fix-script that applies the changes and restarts the container
    fix_script = """#!/bin/bash
echo "Applying camera_manager fix for pose detection..."
cp camera_manager/app.py.backup camera_manager/app.py
echo "Restarting camera-manager container..."
docker-compose restart camera-manager
echo "Fix applied and container restarted."
echo "Check logs with: docker-compose logs -f camera-manager"
"""
    
    with open('fix_pose_detection.sh', 'w') as f:
        f.write(fix_script)
    
    os.chmod('fix_pose_detection.sh', 0o755)
    print("Created fix_pose_detection.sh script to apply the changes")
    
    return True

if __name__ == "__main__":
    add_debug_logging()
