#!/bin/bash

# =========================================================
#  START ALL SERVICES - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  STARTING YOLO POSE API SERVICES"
echo "==========================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or not accessible"
    exit 1
fi

# Check for required model files
if [ ! -f "detector_pose/models/yolo11m-pose.pt" ]; then
    echo "Warning: Pose detection model file not found at detector_pose/models/yolo11m-pose.pt"
    echo "Please make sure the model file is in place before starting services"
fi

if [ ! -f "detector_detections/models/yolo11m.pt" ]; then
    echo "Warning: Object detection model file not found at detector_detections/models/yolo11m.pt"
    echo "Please make sure the model file is in place before starting services"
fi

# Create required directories if they don't exist
echo "Creating required directories..."
mkdir -p videos
mkdir -p output_image
mkdir -p logs/$(date +%Y/%m/%d)
mkdir -p camera_manager/config
mkdir -p shared_image

# Check if there are configuration files
if [ ! "$(ls -A camera_manager/config/*.cfg 2>/dev/null)" ]; then
    echo "Warning: No camera configuration files found in camera_manager/config/"
    echo "Creating a sample configuration file..."
    
    # Create a sample configuration file if none exists
    cat > camera_manager/config/camera_sample.cfg << EOF
[camera]
camera_id = CAM_001
extract_interval = 5
rtsp_url = rtsp://username:password@camera-ip:554/stream
video_path = 
image_path = /app/output_image
source_type = rtsp

[analytics]
enabled = true
pose_detection = true
object_detection = true
EOF
fi

# Build and start services
echo "Building services..."
docker-compose build

echo "Starting services..."
docker-compose up -d

echo "Checking service status..."
docker-compose ps

echo ""
echo "==========================================================="
echo "  SERVICES STARTED SUCCESSFULLY"
echo "==========================================================="
echo ""
echo "Available services:"
echo "- Camera Manager: Manages camera feeds and image extraction"
echo "- Detector Pose: Analyzes images for human poses"
echo "- Detector Detections: Analyzes images for objects"
echo "- Alert Logic: Processes alerts based on detections"
echo ""
echo "Access the Camera Manager API at http://localhost:8010/cameras"
echo "Use './stop_services.sh' to stop all services"
echo "Use 'docker-compose logs -f' to view logs"
echo "==========================================================="
