# Person Tracking with Alert Throttling

This module adds person tracking capabilities to the camera manager service, allowing the system to:

1. Track individual persons across video frames
2. Assign unique IDs to each person 
3. Filter out duplicate alerts for the same person within a configurable time interval
4. Apply tracking for both pose-based and object detection-based alerts

## Configuration

The tracking system can be configured in the camera configuration file:

```ini
[tracking]
enabled = true
# Maximum distance a person can move between frames and still be considered the same person
max_distance_threshold = 100
# Minimum IOU (Intersection over Union) to consider it the same person across frames
min_iou_threshold = 0.3
# Features to use for tracking (spatial = position, appearance = visual features)
use_spatial = true
use_appearance = false

[alerts]
# Minimum seconds between alerts for the same person
alert_interval = 60
# Whether to track unique people for alert suppression
track_unique_people = true
# How long to remember a tracked person after they disappear (seconds)
person_memory = 120
```

## How It Works

1. **Person Tracking**: The system tracks persons across frames using spatial information (bounding box position and overlap). Each tracked person is assigned a unique ID.

2. **Alert Throttling**: When a person triggers an alert, the system records the timestamp. Any subsequent alerts for the same person within the `alert_interval` time window will be suppressed.

3. **Person Memory**: Tracked persons are remembered for the duration specified by `person_memory` (in seconds). After this time, if the person is no longer detected, their tracking information is removed.

## Alert Types

The system can suppress duplicate alerts for various types of alerts, including:

- Hands Up detection
- Weapon detection
- Face covering detection
- Other suspicious activity

## API Integration

The tracking system is seamlessly integrated with the existing alert generation flow. When tracking is enabled, alerts go through an additional filtering step that checks if the same person has triggered an alert recently.
