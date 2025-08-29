#!/usr/bin/env python3
import os
import cv2
import time
import asyncio
import glob
import configparser
import requests
import logging
import json
from datetime import datetime
import pytz
import uuid
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from utils.logger import setup_logger
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import sys
from person_tracker import PersonTracker

# Set up logger
logger = setup_logger("Camera-Manager")

# Define India timezone
india_tz = pytz.timezone('Asia/Kolkata')

# Environment variables
CONFIG_DIR = os.getenv('CONFIG_DIR', 'config')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output_image')
POSE_SERVICE_URL = os.getenv('POSE_SERVICE_URL', 'http://detector-pose:8011/pose/image')
DETECTION_SERVICE_URL = os.getenv('DETECTION_SERVICE_URL', 'http://detector-detections:8013/detect/image')

# Make sure required directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Camera configurations
camera_configs = {}
camera_processes = {}
stop_events = {}
# Person trackers for each camera
camera_trackers = {}

app = FastAPI()

class CameraConfig:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Camera settings
        self.camera_id = self.config.get('camera', 'camera_id')
        self.extract_interval = int(self.config.get('camera', 'extract_interval'))
        self.rtsp_url = self.config.get('camera', 'rtsp_url', fallback='')
        self.video_path = self.config.get('camera', 'video_path', fallback='')
        self.image_path = self.config.get('camera', 'image_path', fallback=OUTPUT_DIR)
        self.source_type = self.config.get('camera', 'source_type', fallback='rtsp')
        # Add loop_video setting for video files
        self.loop_video = self.config.getboolean('camera', 'loop_video', fallback=True)
        # Add camera angle setting
        self.camera_angle = self.config.get('camera', 'camera_angle', fallback='front')
        
        # Analytics settings
        self.analytics_enabled = self.config.getboolean('analytics', 'enabled', fallback=True)
        self.pose_detection = self.config.getboolean('analytics', 'pose_detection', fallback=False)
        self.object_detection = self.config.getboolean('analytics', 'object_detection', fallback=False)
        
        # Tracking settings
        self.tracking_enabled = self.config.getboolean('tracking', 'enabled', fallback=True)
        self.max_distance_threshold = int(self.config.get('tracking', 'max_distance_threshold', fallback='100'))
        self.min_iou_threshold = float(self.config.get('tracking', 'min_iou_threshold', fallback='0.3'))
        self.use_spatial = self.config.getboolean('tracking', 'use_spatial', fallback=True)
        self.use_appearance = self.config.getboolean('tracking', 'use_appearance', fallback=False)
        
        # Alert settings
        self.alert_interval = int(self.config.get('alerts', 'alert_interval', fallback='60'))
        self.track_unique_people = self.config.getboolean('alerts', 'track_unique_people', fallback=True)
        self.person_memory = int(self.config.get('alerts', 'person_memory', fallback='120'))
        
        self.active = True
        
    def update_from_dict(self, config_dict):
        """Update config from dictionary"""
        if 'camera_id' in config_dict:
            self.camera_id = config_dict['camera_id']
            self.config.set('camera', 'camera_id', config_dict['camera_id'])
        
        if 'extract_interval' in config_dict:
            self.extract_interval = int(config_dict['extract_interval'])
            self.config.set('camera', 'extract_interval', str(config_dict['extract_interval']))
        
        if 'rtsp_url' in config_dict:
            self.rtsp_url = config_dict['rtsp_url']
            self.config.set('camera', 'rtsp_url', config_dict['rtsp_url'])
        
        if 'video_path' in config_dict:
            self.video_path = config_dict['video_path']
            self.config.set('camera', 'video_path', config_dict['video_path'])
        
        if 'source_type' in config_dict:
            self.source_type = config_dict['source_type']
            self.config.set('camera', 'source_type', config_dict['source_type'])
        
        if 'loop_video' in config_dict:
            self.loop_video = bool(config_dict['loop_video'])
            self.config.set('camera', 'loop_video', str(config_dict['loop_video']))
            
        if 'image_path' in config_dict:
            self.image_path = config_dict['image_path']
            self.config.set('camera', 'image_path', config_dict['image_path'])
        
        if 'analytics_enabled' in config_dict:
            self.analytics_enabled = bool(config_dict['analytics_enabled'])
            self.config.set('analytics', 'enabled', str(config_dict['analytics_enabled']))
        
        if 'pose_detection' in config_dict:
            self.pose_detection = bool(config_dict['pose_detection'])
            self.config.set('analytics', 'pose_detection', str(config_dict['pose_detection']))
        
        if 'object_detection' in config_dict:
            self.object_detection = bool(config_dict['object_detection'])
            self.config.set('analytics', 'object_detection', str(config_dict['object_detection']))
        
        # Update tracking settings
        if 'tracking_enabled' in config_dict:
            self.tracking_enabled = bool(config_dict['tracking_enabled'])
            self.config.set('tracking', 'enabled', str(config_dict['tracking_enabled']))
            
        if 'max_distance_threshold' in config_dict:
            self.max_distance_threshold = int(config_dict['max_distance_threshold'])
            self.config.set('tracking', 'max_distance_threshold', str(config_dict['max_distance_threshold']))
            
        if 'min_iou_threshold' in config_dict:
            self.min_iou_threshold = float(config_dict['min_iou_threshold'])
            self.config.set('tracking', 'min_iou_threshold', str(config_dict['min_iou_threshold']))
            
        if 'use_spatial' in config_dict:
            self.use_spatial = bool(config_dict['use_spatial'])
            self.config.set('tracking', 'use_spatial', str(config_dict['use_spatial']))
            
        if 'use_appearance' in config_dict:
            self.use_appearance = bool(config_dict['use_appearance'])
            self.config.set('tracking', 'use_appearance', str(config_dict['use_appearance']))
            
        # Update alert settings
        if 'alert_interval' in config_dict:
            self.alert_interval = int(config_dict['alert_interval'])
            self.config.set('alerts', 'alert_interval', str(config_dict['alert_interval']))
            
        if 'track_unique_people' in config_dict:
            self.track_unique_people = bool(config_dict['track_unique_people'])
            self.config.set('alerts', 'track_unique_people', str(config_dict['track_unique_people']))
            
        if 'person_memory' in config_dict:
            self.person_memory = int(config_dict['person_memory'])
            self.config.set('alerts', 'person_memory', str(config_dict['person_memory']))
        
        # Save config back to file
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

def load_camera_configs():
    """Load all camera configuration files"""
    global camera_configs
    config_files = glob.glob(os.path.join(CONFIG_DIR, '*.cfg'))
    
    for config_file in config_files:
        try:
            camera_config = CameraConfig(config_file)
            camera_configs[camera_config.camera_id] = camera_config
            logger.info(f"Loaded camera config: {camera_config.camera_id} from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {str(e)}")

async def process_frame(camera_id, frame, config):
    """Process a video frame according to analytics settings"""
    try:
        # Initialize tracker for this camera if it doesn't exist
        global camera_trackers
        if camera_id not in camera_trackers:
            camera_trackers[camera_id] = PersonTracker(
                max_distance_threshold=config.max_distance_threshold,
                min_iou_threshold=config.min_iou_threshold,
                use_spatial=config.use_spatial,
                use_appearance=config.use_appearance,
                person_memory=config.person_memory
            )
            logger.info(f"Created person tracker for camera {camera_id}")
        else:
            # Update tracker configuration in case it changed
            camera_trackers[camera_id].configure(config)
        
        current_time = datetime.now(india_tz)
        timestamp = current_time.strftime('%Y%m%d_%H%M%S')
        filename = f"source_{timestamp}_{camera_id}.png"
        
        # Use camera-specific image path if provided, otherwise use default OUTPUT_DIR
        output_dir = config.image_path if config.image_path else OUTPUT_DIR
        file_path = os.path.join(output_dir, filename)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save the original frame
        cv2.imwrite(file_path, frame)
        logger.debug(f"Saved frame for {camera_id} at {file_path}")
        
        tasks = []
        responses = []
        
        # Process according to enabled analytics
        if config.analytics_enabled:
            # Only proceed with tracking if tracking is enabled
            if config.tracking_enabled and config.track_unique_people:
                # For now, we collect responses instead of filtering directly
                # Pose detection
                if config.pose_detection:
                    pose_response = await send_to_pose_service(camera_id, file_path, timestamp)
                    if pose_response:
                        responses.append(("poses", pose_response))
                
                # Object detection
                if config.object_detection:
                    detection_response = await send_to_detection_service(camera_id, file_path, timestamp)
                    if detection_response:
                        responses.append(("objects", detection_response))
                
                # Process detections through tracker
                for detection_type, response in responses:
                    if detection_type == "poses":
                        # For pose detection, get poses and alert status
                        if "poses" in response and "alert_status" in response:
                            # Extract the bounding box from the alert if it exists
                            alert_status = response.get("alert_status", {})
                            
                            # Create synthetic detections from pose data for tracking
                            synthetic_detections = []
                            
                            # If there's an alert with a bounding box, use it for tracking
                            if (alert_status and isinstance(alert_status, dict) and 
                                alert_status.get("Image_bb") and 
                                alert_status.get("type_of_alert") != "No_Alert"):
                                
                                for bbox in alert_status.get("Image_bb", []):
                                    synthetic_detections.append({
                                        "class_name": "person",
                                        "bbox": bbox,
                                        "confidence": 0.9
                                    })
                            
                            # If we have synthetic detections, update the tracker
                            if synthetic_detections:
                                person_map = camera_trackers[camera_id].update(synthetic_detections)
                                
                                # Filter the alert based on tracking
                                original_alert = response.get("alert_status")
                                filtered_alert = camera_trackers[camera_id].filter_alerts(original_alert, person_map)
                                response["alert_status"] = filtered_alert
                                
                                # Log if alert was suppressed
                                if (original_alert and isinstance(original_alert, dict) and 
                                    original_alert.get("type_of_alert") != "No_Alert" and 
                                    filtered_alert.get("type_of_alert") == "No_Alert"):
                                    logger.info(f"Pose alert suppressed for camera {camera_id} due to tracking interval")
                    
                    elif response and isinstance(response, dict) and "detections" in response:
                        detections = response.get("detections", [])
                        
                        # Update tracker with detections
                        person_map = camera_trackers[camera_id].update(detections)
                        
                        # Get filtered alert response
                        if "alert_status" in response:
                            original_alert = response["alert_status"]
                            filtered_alert = camera_trackers[camera_id].filter_alerts(original_alert, person_map)
                            response["alert_status"] = filtered_alert
                            
                            # Log if alert was suppressed
                            if (original_alert and isinstance(original_alert, dict) and 
                                original_alert.get("type_of_alert") != "No_Alert" and 
                                filtered_alert.get("type_of_alert") == "No_Alert"):
                                logger.info(f"Object alert suppressed for camera {camera_id} due to tracking interval")
            else:
                # When tracking is disabled, process normally
                # Pose detection
                if config.pose_detection:
                    tasks.append(send_to_pose_service(camera_id, file_path, timestamp))
                    
                # Object detection
                if config.object_detection:
                    tasks.append(send_to_detection_service(camera_id, file_path, timestamp))
                
                # Run tasks concurrently
                if tasks:
                    await asyncio.gather(*tasks)
            
    except Exception as e:
        logger.error(f"Error processing frame from camera {camera_id}: {str(e)}")

async def get_camera_angle(camera_id):
    """Get camera angle from camera config"""
    try:
        config_dir = CONFIG_DIR
        config_file = os.path.join(config_dir, f"{camera_id}.cfg")
        
        if not os.path.exists(config_file):
            # Try to find a config file that contains this camera ID
            config_files = glob.glob(os.path.join(config_dir, "*.cfg"))
            for cf in config_files:
                config = configparser.ConfigParser()
                config.read(cf)
                if 'camera' in config and 'camera_id' in config['camera'] and config['camera']['camera_id'] == camera_id:
                    config_file = cf
                    break
        
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)
            
            if 'camera' in config and 'camera_angle' in config['camera']:
                return config['camera']['camera_angle']
    except Exception as e:
        logger.warning(f"Error getting camera angle: {str(e)}")
    
    return None

async def send_to_pose_service(camera_id, image_path, timestamp):
    """Send image to pose detection service"""
    try:
        # Ensure image exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            return None
        
        # Get camera angle if available
        camera_angle = await get_camera_angle(camera_id)
        if camera_angle:
            logger.info(f"Using camera angle {camera_angle} for {camera_id}")
        
        # Prepare the form data for multipart request (compatible with curl command format)
        form_data = aiohttp.FormData()
        form_data.add_field('file', open(image_path, 'rb'), 
                         filename=os.path.basename(image_path),
                         content_type='image/png')
        form_data.add_field('output_image', '1')
        form_data.add_field('camera_id', camera_id)
        
        # Add camera angle metadata if available
        if camera_angle:
            metadata = json.dumps({'camera_angle': camera_angle})
            form_data.add_field('metadata', metadata)
        
        logger.debug(f"Sending frame to pose service: {POSE_SERVICE_URL}")
        
        # Make async request to pose service
        async with aiohttp.ClientSession() as session:
            async with session.post(POSE_SERVICE_URL, data=form_data) as response:
                if response.status == 200:
                    logger.info(f"Pose detection successful for camera {camera_id}")
                    response_json = await response.json()
                    logger.debug(f"Pose service response: {response_json}")
                    return response_json
                else:
                    error_text = await response.text()
                    logger.error(f"Pose detection failed for camera {camera_id} with status {response.status}: {error_text}")
                    return None
    except Exception as e:
        logger.error(f"Error sending frame to pose service for camera {camera_id}: {str(e)}")
        return None

async def send_to_detection_service(camera_id, image_path, timestamp):
    """Send image to object detection service"""
    try:
        # Ensure image exists
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            return None
        
        # Prepare the form data for multipart request (compatible with curl command format)
        form_data = aiohttp.FormData()
        form_data.add_field('file', open(image_path, 'rb'), 
                         filename=os.path.basename(image_path),
                         content_type='image/png')
        form_data.add_field('output_image', '1')
        form_data.add_field('camera_id', camera_id)
        
        logger.debug(f"Sending frame to detection service: {DETECTION_SERVICE_URL}")
        
        # Make async request to detection service
        async with aiohttp.ClientSession() as session:
            async with session.post(DETECTION_SERVICE_URL, data=form_data) as response:
                if response.status == 200:
                    logger.info(f"Object detection successful for camera {camera_id}")
                    response_json = await response.json()
                    logger.debug(f"Detection service response: {response_json}")
                    return response_json
                else:
                    error_text = await response.text()
                    logger.error(f"Object detection failed for camera {camera_id} with status {response.status}: {error_text}")
                    return None
    except Exception as e:
        logger.error(f"Error sending frame to detection service for camera {camera_id}: {str(e)}")
        return None

async def camera_process(camera_id, config, stop_event):
    """Process camera feed from either RTSP or local video file"""
    # Determine video source based on configuration
    if config.source_type.lower() == 'rtsp':
        source = config.rtsp_url
        logger.info(f"Starting camera process for {camera_id} with RTSP URL: {source}")
    else:  # file source
        source = config.video_path
        logger.info(f"Starting camera process for {camera_id} with local file: {source}")
    
    # Create a VideoCapture instance
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        logger.error(f"Failed to open video source for camera {camera_id}: {source}")
        return
    
    # Get video properties
    is_file = config.source_type.lower() != 'rtsp'
    fps = 0
    total_frames = 0
    frame_interval = 0
    
    if is_file:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            # Calculate how many frames to skip to achieve the desired time interval
            frame_interval = int(fps * config.extract_interval)
            duration = total_frames / fps
            logger.info(f"Video file info: {total_frames} frames, {fps} FPS, {duration:.2f} seconds")
            logger.info(f"Extracting frames every {config.extract_interval} seconds ({frame_interval} frames)")
        else:
            logger.warning(f"Invalid FPS ({fps}) detected, falling back to time-based extraction")
    
    last_capture_time = 0
    frame_count = 0
    next_frame_pos = 0
    
    try:
        while not stop_event.is_set():
            if is_file and fps > 0:
                # For video files with valid FPS, use frame-based extraction
                if frame_interval > 0:
                    # Set position to next frame we want to extract
                    if next_frame_pos >= total_frames:
                        # Reached end of video
                        if config.loop_video:
                            # Loop the video if configured to do so
                            logger.info(f"End of video file reached for camera {camera_id}, restarting (loop_video=True)")
                            next_frame_pos = 0
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            await asyncio.sleep(1)
                            continue
                        else:
                            # Stop processing this video if not configured to loop
                            logger.info(f"End of video file reached for camera {camera_id}, stopping (loop_video=False)")
                            stop_event.set()
                            break
                    
                    # Set position to exact frame we want
                    cap.set(cv2.CAP_PROP_POS_FRAMES, next_frame_pos)
                    ret, frame = cap.read()
                    
                    if ret:
                        # Process the frame asynchronously
                        await process_frame(camera_id, frame, config)
                        # Calculate next position
                        next_frame_pos += frame_interval
                        frame_count += 1
                        # Wait a short time to prevent CPU overload
                        await asyncio.sleep(0.1)
                    else:
                        # Error reading frame
                        logger.warning(f"Failed to read frame at position {next_frame_pos}")
                        next_frame_pos += frame_interval
                        await asyncio.sleep(0.5)
                else:
                    # Fall back to time-based extraction if frame_interval calculation failed
                    await asyncio.sleep(0.1)
            else:
                # For RTSP streams or if FPS is invalid, use time-based extraction
                current_time = time.time()
                time_diff = current_time - last_capture_time
                
                # Check if it's time to extract a frame
                if time_diff >= config.extract_interval:
                    ret, frame = cap.read()
                    if ret:
                        # Process the frame asynchronously
                        await process_frame(camera_id, frame, config)
                        last_capture_time = current_time
                        frame_count += 1
                    else:
                        # For files, handle end of video based on loop_video setting
                        if is_file:
                            if config.loop_video:
                                logger.info(f"End of video file reached for camera {camera_id}, restarting (loop_video=True)")
                                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to beginning of video
                                await asyncio.sleep(1)
                            else:
                                logger.info(f"End of video file reached for camera {camera_id}, stopping (loop_video=False)")
                                stop_event.set()
                                break
                        else:  # For RTSP, attempt reconnection
                            logger.warning(f"Failed to read frame from RTSP stream {camera_id}, attempting reconnection...")
                            cap.release()
                            cap = cv2.VideoCapture(config.rtsp_url)
                            await asyncio.sleep(1)
                else:
                    # Wait a bit to avoid consuming too many resources
                    await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Error in camera process for {camera_id}: {str(e)}")
    finally:
        cap.release()
        logger.info(f"Camera process for {camera_id} stopped after processing {frame_count} frames")

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    try:
        # Load camera configurations
        load_camera_configs()
        
        # Initialize trackers for each camera
        global camera_trackers
        for camera_id, config in camera_configs.items():
            if config.tracking_enabled:
                camera_trackers[camera_id] = PersonTracker(
                    max_distance_threshold=config.max_distance_threshold,
                    min_iou_threshold=config.min_iou_threshold,
                    use_spatial=config.use_spatial,
                    use_appearance=config.use_appearance,
                    person_memory=config.person_memory
                )
                logger.info(f"Initialized person tracker for camera {camera_id}")
        
        # Start processing for each camera
        for camera_id, config in camera_configs.items():
            if config.active:
                stop_event = asyncio.Event()
                stop_events[camera_id] = stop_event
                camera_processes[camera_id] = asyncio.create_task(
                    camera_process(camera_id, config, stop_event)
                )
                logger.info(f"Started processing for camera {camera_id}")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down camera manager...")
    
    # Stop all camera processes
    for camera_id, stop_event in stop_events.items():
        logger.info(f"Stopping camera {camera_id}...")
        stop_event.set()
    
    # Wait for all tasks to complete
    for camera_id, task in camera_processes.items():
        try:
            await task
        except Exception as e:
            logger.error(f"Error stopping camera {camera_id}: {str(e)}")
    
    logger.info("All camera processes stopped")

class CameraConfigRequest(BaseModel):
    """Request model for camera configuration updates"""
    camera_id: str
    extract_interval: int = None
    rtsp_url: str = None
    video_path: str = None
    image_path: str = None
    source_type: str = None
    loop_video: bool = None  # New parameter for video looping control
    analytics_enabled: bool = None
    pose_detection: bool = None
    object_detection: bool = None
    # Tracking parameters
    tracking_enabled: bool = None
    max_distance_threshold: int = None
    min_iou_threshold: float = None
    use_spatial: bool = None
    use_appearance: bool = None
    # Alert parameters
    alert_interval: int = None
    track_unique_people: bool = None
    person_memory: int = None

@app.get("/cameras")
async def get_cameras():
    """List all configured cameras"""
    camera_list = []
    for camera_id, config in camera_configs.items():
        camera_list.append({
            "camera_id": camera_id,
            "rtsp_url": config.rtsp_url,
            "video_path": config.video_path,
            "extract_interval": config.extract_interval,
            "loop_video": config.loop_video,
            "active": config.active,
            "analytics": {
                "enabled": config.analytics_enabled,
                "pose_detection": config.pose_detection,
                "object_detection": config.object_detection
            },
            "tracking": {
                "enabled": config.tracking_enabled,
                "max_distance_threshold": config.max_distance_threshold,
                "min_iou_threshold": config.min_iou_threshold,
                "use_spatial": config.use_spatial,
                "use_appearance": config.use_appearance
            },
            "alerts": {
                "alert_interval": config.alert_interval,
                "track_unique_people": config.track_unique_people,
                "person_memory": config.person_memory
            }
        })
    return {"cameras": camera_list}

@app.get("/camera/{camera_id}")
async def get_camera(camera_id: str):
    """Get specific camera configuration"""
    if camera_id not in camera_configs:
        return {"error": "Camera not found"}
    
    config = camera_configs[camera_id]
    return {
        "camera_id": camera_id,
        "rtsp_url": config.rtsp_url,
        "video_path": config.video_path,
        "extract_interval": config.extract_interval,
        "image_path": config.image_path,
        "source_type": config.source_type,
        "loop_video": config.loop_video,
        "active": config.active,
        "analytics": {
            "enabled": config.analytics_enabled,
            "pose_detection": config.pose_detection,
            "object_detection": config.object_detection
        }
    }

@app.post("/camera")
async def add_camera(config_data: CameraConfigRequest, background_tasks: BackgroundTasks):
    """Add or update camera configuration"""
    camera_id = config_data.camera_id
    config_file = os.path.join(CONFIG_DIR, f"{camera_id}.cfg")
    
    # Validate source configuration
    source_type = config_data.source_type or 'rtsp'
    if source_type.lower() == 'rtsp' and not config_data.rtsp_url:
        return {"error": "RTSP URL is required when source_type is 'rtsp'"}
    if source_type.lower() == 'file' and not config_data.video_path:
        return {"error": "Video path is required when source_type is 'file'"}
        
    # Check if camera already exists
    if camera_id in camera_configs:
        # Update existing config
        config = camera_configs[camera_id]
        config.update_from_dict(config_data.dict(exclude_unset=True))
        
        # Restart camera process if it was already running
        if camera_id in camera_processes and camera_id in stop_events:
            stop_events[camera_id].set()
            await camera_processes[camera_id]
            
            # Start new process
            stop_event = asyncio.Event()
            stop_events[camera_id] = stop_event
            camera_processes[camera_id] = asyncio.create_task(
                camera_process(camera_id, config, stop_event)
            )
            logger.info(f"Restarted camera process for {camera_id}")
            
        return {"message": f"Camera {camera_id} updated successfully"}
    else:
        # Create new config file
        config = configparser.ConfigParser()
        config.add_section('camera')
        config.set('camera', 'camera_id', camera_id)
        config.set('camera', 'extract_interval', str(config_data.extract_interval or 5))
        config.set('camera', 'rtsp_url', config_data.rtsp_url or '')
        config.set('camera', 'video_path', config_data.video_path or '')
        config.set('camera', 'source_type', source_type)
        config.set('camera', 'loop_video', str(config_data.loop_video if config_data.loop_video is not None else True))
        config.set('camera', 'image_path', config_data.image_path or OUTPUT_DIR)
        
        config.add_section('analytics')
        config.set('analytics', 'enabled', str(config_data.analytics_enabled if config_data.analytics_enabled is not None else True))
        config.set('analytics', 'pose_detection', str(config_data.pose_detection if config_data.pose_detection is not None else False))
        config.set('analytics', 'object_detection', str(config_data.object_detection if config_data.object_detection is not None else False))
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        # Load new config
        camera_configs[camera_id] = CameraConfig(config_file)
        
        # Start camera process
        stop_event = asyncio.Event()
        stop_events[camera_id] = stop_event
        camera_processes[camera_id] = asyncio.create_task(
            camera_process(camera_id, camera_configs[camera_id], stop_event)
        )
        logger.info(f"Started camera process for new camera {camera_id}")
        
        return {"message": f"Camera {camera_id} added successfully"}

@app.delete("/camera/{camera_id}")
async def delete_camera(camera_id: str):
    """Delete camera configuration"""
    if camera_id not in camera_configs:
        return {"error": "Camera not found"}
    
    # Stop camera process if running
    if camera_id in camera_processes and camera_id in stop_events:
        stop_events[camera_id].set()
        await camera_processes[camera_id]
        del camera_processes[camera_id]
        del stop_events[camera_id]
    
    # Delete config file
    config_file = os.path.join(CONFIG_DIR, f"{camera_id}.cfg")
    if os.path.exists(config_file):
        os.remove(config_file)
    
    # Remove from configs dict
    del camera_configs[camera_id]
    
    return {"message": f"Camera {camera_id} deleted successfully"}

@app.post("/camera/{camera_id}/toggle")
async def toggle_camera(camera_id: str, active: bool = True):
    """Toggle camera active state"""
    if camera_id not in camera_configs:
        return {"error": "Camera not found"}
    
    config = camera_configs[camera_id]
    
    # Update active state
    config.active = active
    
    # Start or stop camera process
    if active:
        if camera_id not in camera_processes or camera_id not in stop_events:
            stop_event = asyncio.Event()
            stop_events[camera_id] = stop_event
            camera_processes[camera_id] = asyncio.create_task(
                camera_process(camera_id, config, stop_event)
            )
            logger.info(f"Started camera process for {camera_id}")
    else:
        if camera_id in camera_processes and camera_id in stop_events:
            stop_events[camera_id].set()
            await camera_processes[camera_id]
            del camera_processes[camera_id]
            del stop_events[camera_id]
            logger.info(f"Stopped camera process for {camera_id}")
    
    return {"message": f"Camera {camera_id} {'activated' if active else 'deactivated'} successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8010, reload=False)
