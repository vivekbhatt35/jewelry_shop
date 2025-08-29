#!/usr/bin/env python3
import os
import configparser
import sys

def check_camera_config(config_file):
    """Check camera configuration settings"""
    print(f"Checking camera config file: {config_file}")
    
    if not os.path.exists(config_file):
        print(f"Error: Config file not found: {config_file}")
        return False
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # Check if config has required sections
    if 'camera' not in config:
        print("Error: Missing 'camera' section in config")
        return False
    
    if 'analytics' not in config:
        print("Error: Missing 'analytics' section in config")
        return False
    
    # Print camera section
    print("\nCamera section:")
    for key, value in config['camera'].items():
        print(f"  {key} = {value}")
    
    # Print analytics section
    print("\nAnalytics section:")
    for key, value in config['analytics'].items():
        print(f"  {key} = {value}")
    
    # Check tracking section if it exists
    if 'tracking' in config:
        print("\nTracking section:")
        for key, value in config['tracking'].items():
            print(f"  {key} = {value}")
    else:
        print("\nNo tracking section found")
    
    # Check alerts section if it exists
    if 'alerts' in config:
        print("\nAlerts section:")
        for key, value in config['alerts'].items():
            print(f"  {key} = {value}")
    else:
        print("\nNo alerts section found")
    
    # Check specifically for pose detection
    analytics_enabled = config['analytics'].get('enabled', 'False').lower() in ['true', '1', 'yes', 'y']
    pose_detection = config['analytics'].get('pose_detection', 'False').lower() in ['true', '1', 'yes', 'y']
    
    print("\nAnalytics enabled:", analytics_enabled)
    print("Pose detection enabled:", pose_detection)
    
    # Check for tracking settings
    tracking_enabled = False
    track_unique_people = False
    
    if 'tracking' in config:
        tracking_enabled = config['tracking'].get('enabled', 'False').lower() in ['true', '1', 'yes', 'y']
        print("Tracking enabled:", tracking_enabled)
    
    if 'alerts' in config:
        track_unique_people = config['alerts'].get('track_unique_people', 'False').lower() in ['true', '1', 'yes', 'y']
        print("Track unique people:", track_unique_people)
    
    # Check if tracking configuration would allow pose detection
    if analytics_enabled and pose_detection:
        if tracking_enabled and track_unique_people:
            print("\nPose detection will run in tracked mode")
        else:
            print("\nPose detection will run in normal mode")
    else:
        print("\nPose detection is disabled")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_config.py <path_to_config_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    check_camera_config(config_file)
