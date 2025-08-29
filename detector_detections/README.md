# Detector Detections Module Documentation

## Overview

The Detector Detections module is a critical component of our security system that performs object detection on camera frames. It has been updated to work with our newly trained model that uses the following class structure:

- Class 0: person
- Class 1: weapon 
- Class 2: suspicious
- Class 3: helmet
- Class 4: mask

## Key Components

### 1. Model Loading

- The service looks for a YOLOv8 model file (`.pt`) in the `models/` directory
- Prioritizes `best.pt` if available, otherwise uses any `.pt` file
- Falls back to downloading YOLOv8n if no model is found

### 2. API Endpoints

- **`/detect/image`**: Legacy endpoint for direct image uploads
- **`/camera_frame`**: New endpoint for receiving frames from the camera_manager service
- **`/health`**: Health check endpoint that verifies model availability

### 3. Detection Pipeline

For each frame processed:

1. Receive image from camera_manager
2. Save source image for reference
3. Run YOLOv8 inference with our custom model
4. Filter detections based on class-specific confidence thresholds:
   - weapon: 0.15 (very low to catch all potential weapons)
   - suspicious: 0.25
   - helmet/mask: 0.35
   - person: 0.45
5. Generate overlay image with bounding boxes color-coded by class
6. Forward detections to alert-logic service for analysis
7. Clean up images if no alerts are triggered (configurable)

### 4. Integration Points

- **Input**: Receives frames from camera_manager service
- **Output**: Sends detection data to alert-logic service
- **Storage**: Saves source and overlay images to shared volume
- **Monitoring**: Logs all activities with detailed information

## Configuration Options

The service behavior can be customized through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| ALERT_SERVICE_URL | URL for the alert logic service | http://alert-logic:8012/alert |
| OUTPUT_DIR | Directory for saving images | output_image |
| KEEP_NON_ALERT_IMAGES | Whether to keep images that don't trigger alerts | false |

## Class-Based Color Coding

The visualization system uses color-coded bounding boxes:

- Person (class 0): Green
- Weapon (class 1): Red
- Suspicious (class 2): Orange
- Helmet/Mask (classes 3/4): Blue

## Deployment

This service is deployed as part of the overall system using Docker Compose. It exposes port 8013 for API access and shares volumes for images and logs with other services.

## Error Handling

The service implements robust error handling:

- Graceful degradation if model loading fails
- Retries for alert service communication
- Comprehensive logging of all errors
- Proper cleanup of temporary files

## Testing

To test this service independently:

1. Ensure a trained model is in the `models/` directory
2. Start the service: `docker-compose up detector-detections`
3. Send a test frame to `/camera_frame` endpoint
4. Verify detection results in the response and check for generated images
