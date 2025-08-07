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
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if Docker Desktop is running (look for the whale icon in the menu bar)"
    echo "2. Try restarting Docker Desktop"
    echo "3. Run the fix script: ./fix_docker.sh"
    echo ""
    exit 1
fi

# Validate docker-compose.yml
echo "Validating docker-compose configuration..."
if ! docker-compose config > /dev/null 2>&1; then
    echo "Error: Invalid docker-compose.yml configuration"
    echo "Please run ./fix_docker.sh to diagnose and fix issues"
    exit 1
fi
    echo "The error you're seeing might be related to:"
    echo "- Docker daemon not running"
    echo "- Socket permission issues"
    echo "- Docker Desktop needs to be restarted"
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
mkdir -p database/pgdata

# Create a size-optimized database directory
echo "Configuring minimal database storage..."

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

# Check for database initialization script
if [ ! -f "database/init.sql" ]; then
    echo "Warning: Database initialization script not found at database/init.sql"
    echo "Please make sure the database initialization script is in place"
fi

# Parse command line arguments
REBUILD=false

# Process command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --rebuild)
      REBUILD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--rebuild]"
      echo "  --rebuild: Force rebuild of Docker images"
      exit 1
      ;;
  esac
done

# Build and start services
if [ "$REBUILD" = true ]; then
    echo "Rebuilding all services..."
    docker-compose build --no-cache
elif [ ! "$(docker images -q yolo_pose_api-alert-logic 2>/dev/null)" ]; then
    echo "No existing images found. Building services..."
    docker-compose build
else
    echo "Using existing Docker images..."
fi

# Start the database first to ensure it's ready when other services need it
echo "Starting database..."
docker-compose up -d db
echo "Waiting for database to initialize (10 seconds)..."
sleep 10

echo "Starting remaining services..."
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
echo "- PostgreSQL Database: Stores camera configurations and alerts"
echo "- UI Service: Web interface for system management (if enabled)"
echo ""
echo "Access the Camera Manager API at http://localhost:8010/cameras"
echo "Access the Alert Logic API at http://localhost:8012/alerts"
echo "Access the UI interface at http://localhost:3000 (if UI service is enabled)"
echo "Connect to PostgreSQL at localhost:5432 (user: postgres, password: postgres, db: camera_system)"
echo "Use './stop_services.sh' to stop all services"
echo "Use 'docker-compose logs -f' to view logs"
echo "==========================================================="
