#!/bin/bash
# Script to rebuild all services from scratch after cleaning Docker volumes and images

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Rebuilding YOLO Security Detection System${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed. Please install it first.${NC}"
    exit 1
fi

# Ensure we're in the right directory
cd "$(dirname "$0")" || exit 1

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p output_image logs detector_detections/models detector_pose/models

# Check for model files
echo -e "${YELLOW}Checking for model files...${NC}"
if [ ! -f "detector_detections/models/best.pt" ]; then
    echo -e "${YELLOW}Warning: No detection model found at detector_detections/models/best.pt${NC}"
    echo -e "${YELLOW}Please place your trained model there before starting the container.${NC}"
fi

if [ ! -f "detector_pose/models/yolo11m-pose.pt" ]; then
    echo -e "${YELLOW}Warning: No pose model found at detector_pose/models/yolo11m-pose.pt${NC}"
    echo -e "${YELLOW}Please place your pose model there before starting the container.${NC}"
fi

# Clean any old Docker containers to ensure clean rebuild
echo -e "${BLUE}Stopping any running containers...${NC}"
docker-compose down

# Rebuild all images without cache
echo -e "${BLUE}Rebuilding all Docker images from scratch...${NC}"
docker-compose build --no-cache

# Verify build status
if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed. Please check the error messages above.${NC}"
    exit 1
fi

echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${BLUE}----------------------------------------${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Ensure your model files are in the correct locations:"
echo -e "   - Detection model: ${BLUE}detector_detections/models/best.pt${NC}"
echo -e "   - Pose model: ${BLUE}detector_pose/models/yolo11m-pose.pt${NC}"
echo -e "2. Start the services with: ${GREEN}docker-compose up -d${NC}"
echo -e "3. Check logs with: ${GREEN}docker-compose logs -f${NC}"
echo -e "${BLUE}----------------------------------------${NC}"

# Ask if user wants to start services now
read -p "Do you want to start the services now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Starting services...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Services started in the background.${NC}"
    echo -e "Check logs with: ${BLUE}docker-compose logs -f${NC}"
else
    echo -e "${YELLOW}Services not started. Run 'docker-compose up -d' when ready.${NC}"
fi
