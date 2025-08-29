#!/bin/bash
# Script to verify detector_detections setup and configuration

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}Verifying Detector-Detections Configuration${NC}"
echo -e "${BLUE}=============================================${NC}"

# Check directory structure
echo -e "${BLUE}Checking directory structure...${NC}"
MODELS_DIR="detector_detections/models"
if [ ! -d "$MODELS_DIR" ]; then
    echo -e "${YELLOW}Creating models directory: $MODELS_DIR${NC}"
    mkdir -p "$MODELS_DIR"
else
    echo -e "${GREEN}✓ Models directory exists${NC}"
fi

# Check for model file
echo -e "${BLUE}Checking for model file...${NC}"
if [ -f "$MODELS_DIR/best.pt" ]; then
    echo -e "${GREEN}✓ Model file found: $MODELS_DIR/best.pt${NC}"
else
    echo -e "${YELLOW}⚠ No model file found at $MODELS_DIR/best.pt${NC}"
    echo -e "${YELLOW}  You need to place your trained model file in this location.${NC}"
fi

# Check app.py exists
echo -e "${BLUE}Checking for application code...${NC}"
if [ -f "detector_detections/app.py" ]; then
    echo -e "${GREEN}✓ Application code found${NC}"
else
    echo -e "${RED}✗ Application code missing! detector_detections/app.py not found${NC}"
    exit 1
fi

# Check Dockerfile exists
echo -e "${BLUE}Checking Dockerfile...${NC}"
if [ -f "detector_detections/Dockerfile" ]; then
    echo -e "${GREEN}✓ Dockerfile found${NC}"
    # Check if port is correctly exposed
    if grep -q "EXPOSE 8013" "detector_detections/Dockerfile"; then
        echo -e "${GREEN}✓ Port 8013 correctly exposed in Dockerfile${NC}"
    else
        echo -e "${RED}✗ Port 8013 not exposed in Dockerfile!${NC}"
    fi
else
    echo -e "${RED}✗ Dockerfile missing! detector_detections/Dockerfile not found${NC}"
    exit 1
fi

# Check requirements.txt exists
echo -e "${BLUE}Checking requirements file...${NC}"
if [ -f "detector_detections/requirements.txt" ]; then
    echo -e "${GREEN}✓ Requirements file found${NC}"
    # Check if ultralytics is in requirements
    if grep -q "ultralytics" "detector_detections/requirements.txt"; then
        echo -e "${GREEN}✓ Ultralytics package included in requirements${NC}"
    else
        echo -e "${RED}✗ Ultralytics package missing from requirements!${NC}"
    fi
else
    echo -e "${RED}✗ Requirements file missing! detector_detections/requirements.txt not found${NC}"
    exit 1
fi

# Check docker-compose.yml
echo -e "${BLUE}Checking docker-compose.yml...${NC}"
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓ docker-compose.yml found${NC}"
    # Check if detector-detections service is defined
    if grep -q "detector-detections:" "docker-compose.yml"; then
        echo -e "${GREEN}✓ detector-detections service defined in docker-compose.yml${NC}"
    else
        echo -e "${RED}✗ detector-detections service not found in docker-compose.yml!${NC}"
    fi
else
    echo -e "${RED}✗ docker-compose.yml file missing!${NC}"
    exit 1
fi

# Check utils directory
echo -e "${BLUE}Checking utils directory...${NC}"
if [ -d "utils" ]; then
    echo -e "${GREEN}✓ Utils directory found${NC}"
else
    echo -e "${RED}✗ Utils directory missing! This is required for logger.py${NC}"
    exit 1
fi

echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}Configuration verification complete!${NC}"
echo -e "${BLUE}=============================================${NC}"

# Summary
echo -e "${BLUE}Summary:${NC}"
if [ ! -f "$MODELS_DIR/best.pt" ]; then
    echo -e "${YELLOW}- You need to place your trained model file at $MODELS_DIR/best.pt${NC}"
    echo -e "${YELLOW}  This model should have the following classes:${NC}"
    echo -e "${YELLOW}  0: person, 1: weapon, 2: suspicious, 3: helmet, 4: mask${NC}"
fi

echo -e "${GREEN}Ready to build and run:${NC}"
echo -e "1. ${BLUE}chmod +x rebuild_all.sh${NC}"
echo -e "2. ${BLUE}./rebuild_all.sh${NC}"
echo -e "3. Or build individually: ${BLUE}docker-compose build detector-detections${NC}"
echo -e "4. ${BLUE}docker-compose up -d detector-detections${NC}"
