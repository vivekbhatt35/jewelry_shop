#!/bin/bash

# Update tracking configuration and restart services

echo "Updating tracking configuration and restarting services..."

# Update all the Dockerfiles to ensure numpy is installed before other requirements

cat > /Users/vivek/yolo_pose_api/camera_manager/requirements.txt << EOF
fastapi==0.109.1
uvicorn==0.25.0
python-multipart==0.0.6
numpy<2.0.0,>=1.23.5  # Pin numpy to a version compatible with OpenCV
opencv-python==4.9.0.80
requests==2.31.0
configparser==6.0.0
pydantic==2.5.3
python-dotenv==1.0.0
pytz==2024.1
aiohttp==3.9.1
aiortsp==1.3.2
pillow==10.2.0
EOF

# Make sure the camera configuration has tracking enabled and alert interval set correctly
cat > /Users/vivek/yolo_pose_api/camera_manager/config/camera_sample_file.cfg << EOF
[camera]
camera_id = CAM_002
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

# Add more detailed logging to person_tracker.py
sed -i '' 's/logger = logging.getLogger("Camera-Manager")/logger = logging.getLogger("Camera-Manager")\nlogger.setLevel(logging.INFO)/' /Users/vivek/yolo_pose_api/camera_manager/person_tracker.py

# Add debugging statement to the can_alert method in the Person class
sed -i '' 's/def can_alert(self, alert_type, min_interval):/def can_alert(self, alert_type, min_interval):\n        """Check if enough time has passed to alert again"""\n        current_time = time.time()\n        last_alert = self.last_alert_time.get(alert_type, 0)\n        time_diff = current_time - last_alert\n        can_alert = time_diff >= min_interval\n        if last_alert > 0:\n            logger.info(f"Alert check for {alert_type}: last_alert={last_alert}, time_diff={time_diff:.1f}s, min_interval={min_interval}s, can_alert={can_alert}")\n        return can_alert/' /Users/vivek/yolo_pose_api/camera_manager/person_tracker.py

# Start the services
echo "Starting services with docker-compose..."
docker-compose up -d --build

# Wait for services to start
echo "Waiting for services to start..."
sleep 5

# Check the status
docker-compose ps

echo "Services are running. You can check the logs with:"
echo "docker-compose logs -f camera-manager"
