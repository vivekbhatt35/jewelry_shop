#!/bin/bash
# Script to update the YOLOv8 model in the detector-detections service

# Configuration
MODEL_DIR="models"
MODEL_PATH=$1  # First argument should be path to new model file

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if model file was provided
if [ -z "$MODEL_PATH" ]; then
    echo -e "${RED}Error: No model file provided.${NC}"
    echo "Usage: $0 path/to/new_model.pt"
    exit 1
fi

# Check if model file exists
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${RED}Error: Model file not found at '$MODEL_PATH'.${NC}"
    exit 1
fi

# Check if it's a .pt file
if [[ "$MODEL_PATH" != *.pt ]]; then
    echo -e "${YELLOW}Warning: The file does not have a .pt extension. Are you sure this is a YOLOv8 model file?${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 1
    fi
fi

# Create models directory if it doesn't exist
mkdir -p "$MODEL_DIR"

# Get the model filename
MODEL_FILENAME=$(basename "$MODEL_PATH")

# Copy the model to models directory
echo -e "${BLUE}Copying model to $MODEL_DIR/best.pt...${NC}"
cp "$MODEL_PATH" "$MODEL_DIR/best.pt"

# Check if copy was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Model successfully updated to $MODEL_DIR/best.pt${NC}"
    echo -e "${YELLOW}Note: You need to restart the detector-detections service for changes to take effect.${NC}"
    echo -e "${BLUE}To restart: docker-compose restart detector-detections${NC}"
else
    echo -e "${RED}Failed to copy model. Check permissions and try again.${NC}"
    exit 1
fi

# Optional: Check if we're running in a Docker environment
if [ -f "/proc/1/cgroup" ] && grep -q "docker" /proc/1/cgroup; then
    echo -e "${YELLOW}Detected Docker environment.${NC}"
    echo -e "${BLUE}Note: In Docker, mount the models directory as a volume to persist model changes.${NC}"
fi

echo -e "\n${GREEN}Done!${NC}"
