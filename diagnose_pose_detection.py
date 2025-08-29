#!/usr/bin/env python3
"""
Comprehensive diagnostic tool for the YOLO pose detection system.
This script checks all components involved in the pose detection pipeline
and identifies potential issues.
"""

import os
import sys
import json
import subprocess
import configparser
import requests
from datetime import datetime

# Define colors for better output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Print section header
def print_section(title):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")

# Print success message
def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

# Print warning message
def print_warning(message):
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

# Print error message
def print_error(message):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

# Print info message
def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.ENDC}")

def check_docker_services():
    """Check if all required Docker services are running"""
    print_section("Checking Docker Services")
    
    try:
        # Run docker-compose ps to check service status
        result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
        
        if result.returncode != 0:
            print_error("Failed to run docker-compose ps command.")
            print(result.stderr)
            return False
        
        # Parse output
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:  # Only header line
            print_error("No services are running. Start the system with 'docker-compose up -d'")
            return False
        
        services = {}
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 3:
                service_name = parts[0].split('_')[-1]  # Extract service name from container name
                status = parts[-1]
                services[service_name] = status
        
        # Check required services
        required_services = ['camera-manager', 'detector-pose', 'alert-logic']
        
        all_running = True
        for service in required_services:
            if service in services:
                if services[service] == 'Up':
                    print_success(f"Service {service} is running.")
                else:
                    print_error(f"Service {service} is not running properly. Status: {services[service]}")
                    all_running = False
            else:
                print_error(f"Service {service} is not found.")
                all_running = False
        
        return all_running
    
    except Exception as e:
        print_error(f"Error checking Docker services: {str(e)}")
        return False

def check_camera_configs():
    """Check camera configuration files"""
    print_section("Checking Camera Configurations")
    
    config_dir = os.path.join('camera_manager', 'config')
    if not os.path.exists(config_dir):
        print_error(f"Config directory not found: {config_dir}")
        return False
    
    # List all config files
    config_files = [f for f in os.listdir(config_dir) if f.endswith('.cfg')]
    if not config_files:
        print_error(f"No camera config files found in {config_dir}")
        return False
    
    print_info(f"Found {len(config_files)} camera config files.")
    
    pose_enabled_cameras = []
    
    for filename in config_files:
        config_path = os.path.join(config_dir, filename)
        print_info(f"\nAnalyzing {filename}...")
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        # Check required sections
        required_sections = ['camera', 'analytics']
        missing_sections = [s for s in required_sections if s not in config.sections()]
        
        if missing_sections:
            print_error(f"Missing required sections: {', '.join(missing_sections)}")
            continue
        
        # Check analytics settings
        analytics_section = config['analytics']
        
        analytics_enabled = analytics_section.getboolean('enabled', False)
        pose_detection = analytics_section.getboolean('pose_detection', False)
        
        if not analytics_enabled:
            print_warning(f"Analytics disabled for {filename}")
        elif not pose_detection:
            print_warning(f"Pose detection disabled for {filename}")
        else:
            print_success(f"Pose detection enabled for {filename}")
            pose_enabled_cameras.append(config['camera']['camera_id'])
        
        # Check for tracking section
        if 'tracking' in config.sections():
            tracking_section = config['tracking']
            tracking_enabled = tracking_section.getboolean('enabled', False)
            
            if tracking_enabled and 'alerts' in config.sections():
                alerts_section = config['alerts']
                track_unique_people = alerts_section.getboolean('track_unique_people', False)
                
                if track_unique_people:
                    print_info(f"Camera {filename} uses tracking for unique people")
    
    if not pose_enabled_cameras:
        print_error("No cameras have pose detection enabled")
        return False
    
    print_success(f"Found {len(pose_enabled_cameras)} cameras with pose detection enabled: {', '.join(pose_enabled_cameras)}")
    return pose_enabled_cameras

def check_pose_service():
    """Check if pose detection service is responding"""
    print_section("Checking Pose Detection Service")
    
    # Check if the service is accessible locally
    pose_service_url = "http://localhost:8011/pose/image"
    
    try:
        # Just try to access the service (without sending an image)
        response = requests.get(pose_service_url.replace('/pose/image', '/docs'))
        
        if response.status_code == 200:
            print_success(f"Pose service is accessible at {pose_service_url}")
        else:
            print_error(f"Pose service returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Could not connect to pose service at {pose_service_url}")
        return False
    except Exception as e:
        print_error(f"Error checking pose service: {str(e)}")
        return False
    
    return True

def check_logs():
    """Check system logs for errors related to pose detection"""
    print_section("Checking System Logs")
    
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        print_error(f"Log directory not found: {log_dir}")
        return False
    
    # Find the latest log directory
    year_dirs = sorted([d for d in os.listdir(log_dir) if d.isdigit()], reverse=True)
    if not year_dirs:
        print_error("No log year directories found")
        return False
    
    latest_year = year_dirs[0]
    month_dirs = sorted([d for d in os.listdir(os.path.join(log_dir, latest_year)) if d.isdigit()], reverse=True)
    if not month_dirs:
        print_error(f"No log month directories found for year {latest_year}")
        return False
    
    latest_month = month_dirs[0]
    day_dirs = sorted([d for d in os.listdir(os.path.join(log_dir, latest_year, latest_month)) if d.isdigit()], reverse=True)
    if not day_dirs:
        print_error(f"No log day directories found for {latest_year}/{latest_month}")
        return False
    
    latest_day = day_dirs[0]
    log_path = os.path.join(log_dir, latest_year, latest_month, latest_day)
    
    print_info(f"Checking logs in {log_path}")
    
    # Look for pose detection related errors in logs
    pose_detection_errors = []
    camera_manager_errors = []
    alert_logic_errors = []
    
    # Check detector-pose logs
    pose_log_file = os.path.join(log_path, 'detector-pose.log')
    if os.path.exists(pose_log_file):
        with open(pose_log_file, 'r') as f:
            pose_log = f.read()
            
            if 'ERROR' in pose_log:
                error_lines = [l.strip() for l in pose_log.split('\n') if 'ERROR' in l]
                pose_detection_errors.extend(error_lines[-5:])  # Show last 5 errors
                
                print_error(f"Found {len(error_lines)} errors in pose detection logs")
                for err in pose_detection_errors:
                    print_error(f"  - {err}")
            else:
                print_success("No errors found in pose detection logs")
    else:
        print_warning(f"Pose detection log file not found: {pose_log_file}")
    
    # Check camera-manager logs for pose service calls
    camera_log_file = os.path.join(log_path, 'camera-manager.log')
    if os.path.exists(camera_log_file):
        with open(camera_log_file, 'r') as f:
            camera_log = f.read()
            
            pose_service_calls = [l.strip() for l in camera_log.split('\n') if 'pose service' in l.lower()]
            pose_detection_calls = [l.strip() for l in camera_log.split('\n') if 'pose detection' in l.lower()]
            
            if pose_service_calls:
                print_success(f"Found {len(pose_service_calls)} pose service calls in camera logs")
                for call in pose_service_calls[-3:]:  # Show last 3 calls
                    print_info(f"  - {call}")
            else:
                print_error("No pose service calls found in camera logs")
                
            if pose_detection_calls:
                print_success(f"Found {len(pose_detection_calls)} pose detection references in camera logs")
                for call in pose_detection_calls[-3:]:  # Show last 3 references
                    print_info(f"  - {call}")
            else:
                print_error("No pose detection references found in camera logs")
                
            if 'ERROR' in camera_log:
                error_lines = [l.strip() for l in camera_log.split('\n') if 'ERROR' in l]
                camera_manager_errors.extend(error_lines[-5:])  # Show last 5 errors
                
                print_error(f"Found {len(error_lines)} errors in camera manager logs")
                for err in camera_manager_errors:
                    print_error(f"  - {err}")
            else:
                print_success("No errors found in camera manager logs")
    else:
        print_warning(f"Camera manager log file not found: {camera_log_file}")
    
    # Check alert-logic logs for pose processing
    alert_log_file = os.path.join(log_path, 'alert-logic.log')
    if os.path.exists(alert_log_file):
        with open(alert_log_file, 'r') as f:
            alert_log = f.read()
            
            pose_references = [l.strip() for l in alert_log.split('\n') if 'pose' in l.lower()]
            
            if pose_references:
                print_success(f"Found {len(pose_references)} pose references in alert logs")
                for ref in pose_references[-3:]:  # Show last 3 references
                    print_info(f"  - {ref}")
            else:
                print_error("No pose references found in alert logs")
                
            if 'ERROR' in alert_log:
                error_lines = [l.strip() for l in alert_log.split('\n') if 'ERROR' in l]
                alert_logic_errors.extend(error_lines[-5:])  # Show last 5 errors
                
                print_error(f"Found {len(error_lines)} errors in alert logic logs")
                for err in alert_logic_errors:
                    print_error(f"  - {err}")
            else:
                print_success("No errors found in alert logic logs")
    else:
        print_warning(f"Alert logic log file not found: {alert_log_file}")
    
    return len(pose_detection_errors) == 0 and len(camera_manager_errors) == 0 and len(alert_logic_errors) == 0

def check_output_images():
    """Check for pose detection output images"""
    print_section("Checking Output Images")
    
    output_dir = 'output_image'
    if not os.path.exists(output_dir):
        print_error(f"Output directory not found: {output_dir}")
        return False
    
    # Count images by type
    files = os.listdir(output_dir)
    source_images = [f for f in files if f.startswith('source_')]
    overlay_images = [f for f in files if f.startswith('overlay_')]
    alert_images = [f for f in files if f.startswith('alert_')]
    
    print_info(f"Found {len(source_images)} source images")
    print_info(f"Found {len(overlay_images)} overlay images")
    print_info(f"Found {len(alert_images)} alert images")
    
    # Check for pose detection in overlay images (basic heuristic)
    if overlay_images:
        print_success("Found overlay images which may indicate pose detection is working")
    else:
        print_warning("No overlay images found")
    
    return True

def fix_pose_detection():
    """Apply fixes to common pose detection issues"""
    print_section("Fixing Pose Detection")
    
    fixes_applied = False
    
    # Fix 1: Ensure all cameras have pose_detection=True
    config_dir = os.path.join('camera_manager', 'config')
    if os.path.exists(config_dir):
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.cfg')]
        
        for filename in config_files:
            config_path = os.path.join(config_dir, filename)
            
            config = configparser.ConfigParser()
            config.read(config_path)
            
            if 'analytics' in config.sections():
                analytics_section = config['analytics']
                
                if analytics_section.get('enabled', 'False').lower() != 'true' or analytics_section.get('pose_detection', 'False').lower() != 'true':
                    print_info(f"Updating config for {filename} to enable pose detection")
                    
                    # Create backup
                    backup_path = config_path + '.backup'
                    if not os.path.exists(backup_path):
                        with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
                            dst.write(src.read())
                    
                    # Update config
                    analytics_section['enabled'] = 'True'
                    analytics_section['pose_detection'] = 'True'
                    
                    with open(config_path, 'w') as f:
                        config.write(f)
                    
                    print_success(f"Updated {filename} to enable pose detection")
                    fixes_applied = True
    
    # Fix 2: Add missing tracking section if needed
    for filename in config_files:
        config_path = os.path.join(config_dir, filename)
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        if 'tracking' not in config.sections():
            print_info(f"Adding missing tracking section to {filename}")
            
            # Create backup if not already created
            backup_path = config_path + '.backup'
            if not os.path.exists(backup_path):
                with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            # Add tracking section
            config['tracking'] = {
                'enabled': 'false',
                'max_distance_threshold': '200',
                'min_iou_threshold': '0.1',
                'use_spatial': 'true',
                'use_appearance': 'true'
            }
            
            with open(config_path, 'w') as f:
                config.write(f)
            
            print_success(f"Added tracking section to {filename}")
            fixes_applied = True
    
    # Fix 3: Create restart script for services
    restart_script = """#!/bin/bash
echo "Restarting pose detection services..."
docker-compose restart detector-pose
docker-compose restart camera-manager
docker-compose restart alert-logic
echo "Services restarted."
"""
    
    restart_path = 'restart_pose_detection.sh'
    with open(restart_path, 'w') as f:
        f.write(restart_script)
    
    os.chmod(restart_path, 0o755)
    print_success(f"Created {restart_path} to restart services")
    
    if fixes_applied:
        print_info("Fixes applied. Run ./restart_pose_detection.sh to apply changes")
    else:
        print_info("No fixes were needed")
    
    return True

def main():
    print_section("YOLO Pose Detection System Diagnostics")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run checks
    services_ok = check_docker_services()
    cameras_ok = check_camera_configs()
    pose_service_ok = check_pose_service()
    logs_ok = check_logs()
    output_ok = check_output_images()
    
    # Summarize findings
    print_section("Diagnostic Summary")
    
    if services_ok:
        print_success("Docker services are running correctly")
    else:
        print_error("Issues found with Docker services")
    
    if cameras_ok:
        print_success("Camera configurations are correct")
    else:
        print_error("Issues found with camera configurations")
    
    if pose_service_ok:
        print_success("Pose detection service is responsive")
    else:
        print_error("Issues found with pose detection service")
    
    if logs_ok:
        print_success("No critical errors found in logs")
    else:
        print_error("Issues found in system logs")
    
    if output_ok:
        print_success("Output images directory is accessible")
    else:
        print_error("Issues found with output images")
    
    # Suggest fixes if needed
    if not (services_ok and cameras_ok and pose_service_ok and logs_ok and output_ok):
        print("\nRecommended actions:")
        print_info("1. Run the fix_pose_detection.sh script to apply recommended fixes")
        print_info("2. If issues persist, run './restart_pose_detection.sh' to restart services")
        print_info("3. Check the detailed logs for more information")
        
        # Offer to fix issues
        print("\nWould you like to apply fixes now? (y/n)")
        response = input().strip().lower()
        
        if response == 'y':
            fix_pose_detection()
    else:
        print_success("\nAll systems appear to be functioning correctly!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
