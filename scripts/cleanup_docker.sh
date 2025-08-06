#!/bin/bash

# =========================================================
#  CLEANUP DOCKER RESOURCES - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  CLEANING UP DOCKER RESOURCES"
echo "==========================================================="

# Stop all running containers in this project
echo "Stopping any running containers..."
docker-compose -p yolo_pose down

# Remove all associated images
echo "Removing project images..."
docker rmi -f yolo_pose-detector-pose yolo_pose-detector-detections yolo_pose-alert-logic 2>/dev/null || true

# Prune Docker system
echo "Pruning Docker system..."
docker system prune -f

# Create necessary directories
echo "Creating directories..."
mkdir -p output_image logs
mkdir -p detector_pose/models detector_detections/models utils
chmod -R 777 output_image logs

echo "==========================================================="
echo "  CLEANUP COMPLETE"
echo "==========================================================="
echo ""
echo "All Docker resources have been cleaned up."
echo "Ready to rebuild with './start_services.sh'"
echo "==========================================================="
