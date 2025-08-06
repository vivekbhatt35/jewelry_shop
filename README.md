# YOLO Pose API

A modular system for camera stream processing, pose detection, object detection, and alert management.

## System Architecture

This system consists of four main services:

1. **Camera Manager**: Manages video sources (RTSP streams or local video files), extracts frames, and sends them to detection services.
2. **Detector Pose**: Analyzes images for human pose detection using YOLO models.
3. **Detector Detections**: Identifies objects in images using YOLO models.
4. **Alert Logic**: Processes detection results and generates alerts based on business rules.

## Quick Start

To start all services:
```bash
./start_services.sh
```

To stop all services:
```bash
./stop_services.sh
```

## Directory Structure

```
├── alert_logic/             # Alert processing service
│   ├── app.py               # FastAPI application
│   ├── Dockerfile           # Container definition
│   ├── requirements.txt     # Python dependencies
│   └── logic/               # Alert business logic
│       ├── detection_analysis.py
│       └── pose_analysis.py
├── camera_manager/          # Camera stream management service
│   ├── app.py               # FastAPI application
│   ├── Dockerfile           # Container definition
│   ├── requirements.txt     # Python dependencies
│   └── config/              # Camera configuration files
│       ├── camera_sample.cfg
│       └── camera_sample_file.cfg
├── detector_detections/      # Object detection service
│   ├── app.py               # FastAPI application
│   ├── Dockerfile           # Container definition
│   ├── requirements.txt     # Python dependencies
│   └── models/              # YOLO models for object detection
├── detector_pose/           # Pose detection service
│   ├── app.py               # FastAPI application
│   ├── Dockerfile           # Container definition
│   ├── requirements.txt     # Python dependencies
│   └── models/              # YOLO models for pose detection
├── logs/                    # Service logs
├── output_image/            # Output images from detection services
├── scripts/                 # Utility scripts for testing and maintenance
│   ├── cleanup_docker.sh    # Complete Docker cleanup
│   ├── fix_*.sh             # Various fix scripts
│   ├── test_*.sh            # Test scripts
│   └── README.md            # Documentation for scripts
├── shared_image/            # Shared images between services
├── videos/                  # Local video files for processing
├── utils/                   # Shared utilities
│   ├── __init__.py
│   └── logger.py            # Common logging configuration
├── docker-compose.yml       # Service orchestration
├── start_services.sh        # Start all services
└── stop_services.sh         # Stop all services
```

## System Flow

1. Camera Manager extracts frames from video sources at regular intervals
2. Based on camera configuration, frames are sent to Detector Pose and/or Detector Detections
3. Detection services process frames and identify objects/poses
4. If suspicious activity is detected, results are forwarded to Alert Logic
5. Alert Logic analyzes combined results and generates alerts when necessary
6. Processed images with annotations are saved to the output_image directory

## Quick Start

### Prerequisites
- Docker and Docker Compose installed

### Setup and Run

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd yolo_pose_api
   ```

2. **Place YOLO model files**:
   - Put YOLO pose model in `detector_pose/models/` (yolo11m-pose.pt)
   - Put YOLO detection model in `detector_detections/models/` (yolo11m.pt)

3. **Configure cameras**:
   Edit or create camera configuration files in `camera_manager/config/`

4. **Build and start services**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

5. **Check service status**:
   ```bash
   docker-compose ps
   ```

For more detailed instructions, see [Camera Manager README](./camera_manager/README.md).

## API Endpoints

### Camera Manager (port 8010)
- `GET /cameras` - List all cameras
- `GET /camera/{camera_id}` - Get specific camera
- `POST /camera` - Add/update camera
- `DELETE /camera/{camera_id}` - Delete camera
- `POST /camera/{camera_id}/toggle` - Enable/disable camera

### Pose Detection (port 8011)
- `POST /pose/image` - Detect poses in an image

### Object Detection (port 8013)
- `POST /detect/image` - Detect objects in an image

### Alert Logic (port 8012)
- `POST /alert` - Process detection results and generate alerts

## Maintenance

```bash
# Clean up old images (older than 7 days)
./camera_manager/cleanup_images.sh 7

# View logs
ls -la logs/$(date +%Y/%m/%d)/

# Stop all services
docker-compose down
```
