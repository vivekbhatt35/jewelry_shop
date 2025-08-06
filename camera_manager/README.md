# Camera Manager

A service for managing multiple camera streams and local video files, extracting frames at specified intervals, and sending them to detection services for analysis.

## Features

- Support for both RTSP camera streams and local video files
- Configuration via .cfg files for each camera source
- Frame extraction at configurable intervals
- Integration with pose detection and object detection services
- REST API for managing cameras
- Volume mount compatibility with other services

## Configuration Files

Each camera has its own configuration file in the `config` directory with the following format:

```ini
[camera]
camera_id = CAM_001                             # Unique ID for the camera
extract_interval = 5                            # Frame extraction interval in seconds
rtsp_url = rtsp://username:password@ip:port/path # For RTSP sources
video_path = /app/videos/sample.mp4             # For local video files
image_path = /app/output_image                  # Where to store captured frames
source_type = rtsp                              # Either 'rtsp' or 'file'

[analytics]
enabled = true                                  # Enable analytics processing
pose_detection = true                           # Send to pose detection service
object_detection = true                         # Send to object detection service
```

## API Endpoints

- `GET /cameras` - List all configured cameras
- `GET /camera/{camera_id}` - Get specific camera configuration
- `POST /camera` - Add or update a camera configuration
- `DELETE /camera/{camera_id}` - Delete a camera configuration
- `POST /camera/{camera_id}/toggle?active=true|false` - Activate or deactivate a camera

## Example API Usage

```bash
# Add a new RTSP camera
curl -X POST http://localhost:8010/camera \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "CAM_003",
    "extract_interval": 10,
    "rtsp_url": "rtsp://admin:password@192.168.1.100:554/stream",
    "source_type": "rtsp",
    "pose_detection": true,
    "object_detection": false
  }'

# Add a local video file source
curl -X POST http://localhost:8010/camera \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "CAM_004",
    "extract_interval": 5,
    "video_path": "/app/videos/sample.mp4",
    "source_type": "file",
    "pose_detection": true,
    "object_detection": true
  }'
  
# Get list of all cameras
curl http://localhost:8010/cameras

# Delete a camera
curl -X DELETE http://localhost:8010/camera/CAM_004
```

## Running the Services

### Prerequisites
- Docker and Docker Compose installed
- YOLO model files in appropriate directories:
  - `detector_pose/models/` should contain YOLO pose model file (yolo11m-pose.pt)
  - `detector_detections/models/` should contain YOLO detection model file (yolo11m.pt)

### Steps to Run All Services

1. **Prepare Camera Configuration Files**:
   - Create or edit camera configuration files in `camera_manager/config/` directory
   - Ensure each camera has a unique ID and appropriate source type (rtsp/file)
   - For local video files, place them in the `videos/` directory

2. **Build and Start Services**:
   ```bash
   # Build all services (required on first run or after code changes)
   docker-compose build
   
   # Start all services in detached mode
   docker-compose up -d
   
   # To see the logs from all services
   docker-compose logs -f
   
   # To see logs from a specific service
   docker-compose logs -f camera-manager
   ```

3. **Verify Services Are Running**:
   ```bash
   # Check container status
   docker-compose ps
   
   # Test camera manager API
   curl http://localhost:8010/cameras
   
   # Test pose detection service
   curl -X POST http://localhost:8011/pose/image -F "file=@/path/to/image.jpg" -F "output_image=1" -F "camera_id=TEST"
   
   # Test object detection service
   curl -X POST http://localhost:8013/detect/image -F "file=@/path/to/image.jpg" -F "output_image=1" -F "camera_id=TEST"
   ```

4. **Stopping Services**:
   ```bash
   # Stop all services but preserve containers
   docker-compose stop
   
   # Stop and remove containers
   docker-compose down
   
   # Stop and remove containers and images (complete cleanup)
   docker-compose down --rmi all
   ```

5. **Maintenance**:
   ```bash
   # Clean up old images (older than 7 days)
   ./camera_manager/cleanup_images.sh 7
   
   # View logs
   ls -la logs/$(date +%Y/%m/%d)/
   ```
