# Person Tracking with Alert Throttling - Implementation Summary

## What's Been Implemented

1. **Person Tracking System**
   - Created `person_tracker.py` module to track individuals across video frames
   - Implemented tracking based on bounding box positions using IOU and distance metrics
   - Created unique IDs for each tracked person
   - Configured tracking parameters for fine-tuning (distance threshold, IOU threshold)

2. **Alert Throttling**
   - Added alert interval configuration to prevent duplicate alerts for the same person
   - Implemented filtering logic that suppresses alerts within the configured interval
   - Added memory capability to remember people who have left the scene temporarily

3. **Configuration System**
   - Extended `CameraConfig` class to support tracking and alert settings
   - Added tracking and alert sections to camera config files
   - Implemented configuration parameters:
     - `alert_interval`: Time between allowed alerts for the same person
     - `track_unique_people`: Enable/disable tracking functionality
     - `person_memory`: How long to remember a person after they leave

4. **API Updates**
   - Updated `get_cameras` endpoint to include tracking and alert settings
   - Extended `CameraConfigRequest` model to support tracking parameters

5. **Testing Tools**
   - Created `test_tracking.py` for standalone testing of the tracking functionality
   - Added `start_camera_with_tracking.sh` script for easy deployment with tracking enabled

## How to Use

1. **Configure Tracking Parameters**
   - Edit `camera_manager/config/camera_sample_file.cfg` to set:
     - Tracking settings (distance threshold, IOU threshold)
     - Alert interval (seconds between alerts for the same person)

2. **Start the Service with Tracking**
   - Run the provided script: `./start_camera_with_tracking.sh`
   - This script ensures the tracking configuration exists and starts the service

3. **Testing the Tracking**
   - Use `test_tracking.py` with a test video to visualize the tracking
   - Example: `python camera_manager/test_tracking.py --video test.mp4 --interval 60`

## How It Works

1. Each detected person is assigned a unique ID based on their position in the frame
2. When a person triggers an alert, the system records the timestamp
3. Subsequent alerts for the same person are suppressed if they occur within the configured time interval
4. Tracking works with both pose-based alerts (hands up) and object-based alerts (weapons, face coverings)

## Benefits

- Reduced alert fatigue by preventing duplicate alerts for the same person
- Configurable intervals to match security requirements
- Tracking across frames maintains person identity even with movement
- Works with all existing alert types (no changes needed to detection services)

## Configuration Parameters

```ini
[tracking]
enabled = true
max_distance_threshold = 100  # Max pixel distance between frames
min_iou_threshold = 0.3       # Minimum intersection over union
use_spatial = true            # Use position for tracking
use_appearance = false        # Use visual features for tracking (not implemented yet)

[alerts]
alert_interval = 60           # Seconds between alerts for the same person
track_unique_people = true    # Enable person tracking for alerts
person_memory = 120           # Remember person for this many seconds after they disappear
```
