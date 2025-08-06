# Utility Scripts for YOLO Pose API

This folder contains utility scripts for various maintenance, testing, and troubleshooting tasks for the YOLO Pose API system.

## Main Scripts (in root folder)

These main scripts should be used for regular operation:

- `../start_services.sh` - Starts all services
- `../stop_services.sh` - Stops all running services

## Utility Scripts

These scripts are specialized for specific tasks:

### Maintenance

- `cleanup_docker.sh` - Completely cleans up Docker resources including images and containers
- `cleanup_unused_images.sh` - Removes source and overlay images that don't have corresponding alerts
- `test_cleanup.sh` - Tests the image cleanup functionality
- `restart_services.sh` - Restarts all services without rebuilding

### Testing

- `test_alert.sh` - Tests the alert functionality
- `test_hands_up_detection.sh` - Tests specifically the hands-up pose detection
- `test_direct.sh` - Performs a direct test of the API endpoints
- `test_alert_naming.sh` - Tests the alert image naming format

### Fixing Issues

- `fix_alert_service.sh` - Fixes issues with the alert service
- `fix_alert_naming.sh` - Fixes the alert image naming format
- `fix_hands_up_detection.sh` - Adjusts thresholds for hands-up detection
- `fix_alert_overload.sh` - Fixes issues with alert throttling
- `fix_tracking.sh` - Fixes person tracking issues

### Camera Management

- `start_camera_with_tracking.sh` - Starts the camera with tracking enabled

### System Improvements

- `restart_with_improvements.sh` - Restarts with general improvements
- `restart_with_frame_fix.sh` - Restarts with frame extraction fixes

## Usage

Most scripts can be run directly:

```bash
./script_name.sh
```

For example:

```bash
./test_hands_up_detection.sh
```

Some scripts may require Docker services to be running first.
