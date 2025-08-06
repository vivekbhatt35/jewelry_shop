#!/bin/bash
# Script to start the camera manager service with tracking functionality

echo "Starting Camera Manager with Person Tracking and Alert Interval Control"
echo "----------------------------------------------------------------------"

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install it first."
    exit 1
fi

# Make the script directory the working directory
cd "$(dirname "$0")"

# Stop any existing camera-manager container
echo "Stopping any existing camera-manager service..."
docker-compose stop camera-manager

# Ensure the sample camera config file has the tracking and alert sections
CONFIG_FILE="camera_manager/config/camera_sample_file.cfg"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default camera configuration file..."
    mkdir -p camera_manager/config
    cat > "$CONFIG_FILE" << EOF
[camera]
camera_id = CAM_001
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
EOF
    echo "Created default camera configuration."
else
    # Check if the tracking and alerts sections exist in the config file
    if ! grep -q "\[tracking\]" "$CONFIG_FILE"; then
        echo "Adding tracking configuration to $CONFIG_FILE..."
        cat >> "$CONFIG_FILE" << EOF

[tracking]
enabled = true
max_distance_threshold = 100
min_iou_threshold = 0.3
use_spatial = true
use_appearance = false
EOF
    fi
    
    if ! grep -q "\[alerts\]" "$CONFIG_FILE"; then
        echo "Adding alerts configuration to $CONFIG_FILE..."
        cat >> "$CONFIG_FILE" << EOF

[alerts]
alert_interval = 60
track_unique_people = true
person_memory = 120
EOF
    fi
fi

# Build and start the camera-manager service
echo "Building and starting camera-manager service with tracking..."
docker-compose up -d --build camera-manager

# Check if the service started successfully
if [ $? -eq 0 ]; then
    echo "Camera Manager service started successfully with tracking functionality."
    echo "Alert interval is set to $(grep "alert_interval" "$CONFIG_FILE" | cut -d= -f2) seconds."
    echo "To change the alert interval, edit $CONFIG_FILE and restart the service."
else
    echo "Error: Failed to start Camera Manager service."
    exit 1
fi

# Show the logs
echo "Showing camera-manager logs. Press Ctrl+C to exit."
docker-compose logs -f camera-manager
