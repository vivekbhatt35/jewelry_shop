from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from logic.pose_analysis import hands_up_detect, get_person_bboxes, draw_bboxes
from logic.detection_analysis import analyze_detections, get_detection_bboxes, draw_detection_boxes
from datetime import datetime
import pytz
import cv2
import os
import json
import uuid
import threading
import time
import traceback
from utils.logger import setup_logger
from image_cleaner import ImageCleaner
from database.db_utils import AlertRepository

# Monkey patch cv2.imwrite to log all file writes AND fix UUID-based filenames
original_imwrite = cv2.imwrite
def patched_imwrite(filename, img):
    # Check for UUID-based alertoverlay pattern
    if 'alertoverlay_' in filename:
        logger.warning(f"INTERCEPTING ALERTOVERLAY FILENAME: {filename}")
        stack = traceback.format_stack()
        logger.warning(f"STACK TRACE: {''.join(stack[-5:-1])}")
        
        # Try to create a proper alert name instead
        try:
            # Extract camera_id from somewhere in the context
            camera_id = "UNKNOWN"
            # Look through stack frames to find camera_id in locals or function args
            import inspect
            frame = inspect.currentframe().f_back  # Get calling frame
            if 'camera_id' in frame.f_locals:
                camera_id = frame.f_locals['camera_id']
                logger.warning(f"Found camera_id in frame locals: {camera_id}")
            
            # Create standardized name
            timestamp = datetime.now(india_tz).strftime("%H%M%S")
            alert_type_str = "Alert"  # Default
            
            # Look for alert type in frame locals
            if 'result_alerts' in frame.f_locals and frame.f_locals['result_alerts']:
                alert_type_str = '_'.join(frame.f_locals['result_alerts'])
                logger.warning(f"Found alert_type in frame: {alert_type_str}")
            
            new_filename = os.path.join(OUTPUT_DIR, f"alert_{camera_id}_{timestamp}_{alert_type_str}.jpg")
            logger.warning(f"RENAMED ALERTOVERLAY TO STANDARDIZED NAME: {new_filename}")
            return original_imwrite(new_filename, img)
        except Exception as e:
            logger.error(f"Error trying to rename alertoverlay file: {str(e)}")
            # Create a fallback standardized name
            timestamp = datetime.now(india_tz).strftime("%H%M%S")
            new_filename = os.path.join(OUTPUT_DIR, f"alert_UNKNOWN_{timestamp}_Alert.jpg")
            logger.warning(f"Using fallback standardized name: {new_filename}")
            return original_imwrite(new_filename, img)
    
    return original_imwrite(filename, img)
    # Check for UUID-based alertoverlay pattern
    if 'alertoverlay_' in filename:
        logger.warning(f"INTERCEPTING ALERTOVERLAY FILENAME: {filename}")
        stack = traceback.format_stack()
        logger.warning(f"STACK TRACE: {''.join(stack[-5:-1])}")
        
        # Try to create a proper alert name instead
        try:
            # Extract camera_id from somewhere in the context
            camera_id = "UNKNOWN"
            # Look through stack frames to find camera_id in locals or function args
            frame = traceback._getframe(1)  # Get calling frame
            if 'camera_id' in frame.f_locals:
                camera_id = frame.f_locals['camera_id']
                logger.warning(f"Found camera_id in frame locals: {camera_id}")
            
            # Create standardized name
            timestamp = datetime.now(india_tz).strftime("%H%M%S")
            alert_type_str = "Alert"  # Default
            
            # Look for alert type in frame locals
            if 'result_alerts' in frame.f_locals and frame.f_locals['result_alerts']:
                alert_type_str = '_'.join(frame.f_locals['result_alerts'])
                logger.warning(f"Found alert_type in frame: {alert_type_str}")
            
            new_filename = os.path.join(OUTPUT_DIR, f"alert_{camera_id}_{timestamp}_{alert_type_str}.jpg")
            logger.warning(f"RENAMED ALERTOVERLAY TO STANDARDIZED NAME: {new_filename}")
            return original_imwrite(new_filename, img)
        except Exception as e:
            logger.error(f"Error trying to rename alertoverlay file: {str(e)}")
            # Continue with original name if rename fails
    
    return original_imwrite(filename, img)
cv2.imwrite = patched_imwrite

# Set up logger
logger = setup_logger("Alert-Logic")

# Define India timezone
india_tz = pytz.timezone('Asia/Kolkata')

app = FastAPI()
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output_image')
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/alert")
async def create_alert(
    camera_id: str = Form(...),
    detection_type: str = Form(...),
    date_time: str = Form(...),
    image_source: str = Form(...),
    image_overlay: str = Form(None),
    poses: str = Form(None),
    detections: str = Form(None)
):
    try:
        logger.info(f"Processing alert from camera {camera_id}, type: {detection_type}")
        
        # Fix path handling - use basename and absolute path
        image_basename = os.path.basename(image_source)
        image_path = os.path.join(OUTPUT_DIR, image_basename)
        
        logger.debug(f"Looking for source image at: {image_path}")
        logger.debug(f"Original image path received: {image_source}")
        
        # First check if the original path exists (more reliable)
        if os.path.exists(image_source):
            logger.info(f"Found image at original path: {image_source}")
            image_path = image_source
        # Then check the modified path
        elif not os.path.exists(image_path):
            error_msg = f"Image not found at either path: {image_source} or {image_path}"
            logger.error(error_msg)
            return JSONResponse(content={
                "error": error_msg,
                "paths_checked": [image_source, image_path]
            }, status_code=400)

        # Load the image with additional error checking
        logger.debug(f"Attempting to read image from {image_path}")
        try:
            base_img = cv2.imread(image_path)
            if base_img is None or base_img.size == 0:
                error_msg = f"Failed to load valid image from {image_path}"
                logger.error(error_msg)
                return JSONResponse(content={
                    "error": error_msg,
                    "path_checked": image_path
                }, status_code=400)
            
            logger.debug(f"Image loaded successfully, shape: {base_img.shape}")
        except Exception as e:
            error_msg = f"Error reading image: {str(e)}"
            logger.error(error_msg)
            return JSONResponse(content={
                "error": error_msg,
                "path_checked": image_path
            }, status_code=400)
        
        # Process based on detection type
        result_alerts = []
        image_bb = []
        
        if detection_type.lower() == "poses" and poses:
            # Process pose-based alerts (hands up)
            poses_list = json.loads(poses)
            person_alert_indices = hands_up_detect(poses_list)
            
            if person_alert_indices:
                result_alerts.append("Hands_Up")
                logger.info(f"Alert detected: Hands_Up for persons {person_alert_indices}")
                
                # Create timestamp-based filename for alert right away to ensure it's used
                alert_type_str = "Hands_Up"
                timestamp = datetime.now(india_tz).strftime("%H%M%S")
                alert_filename = f"alert_{camera_id}_{timestamp}_{alert_type_str}.jpg"
                logger.info(f"Created standardized alert filename: {alert_filename}")
                
                # Draw bounding boxes for alerted persons
                person_bboxes = get_person_bboxes(poses_list)
                base_img = draw_bboxes(base_img, person_bboxes, person_alert_indices, color=(0, 0, 255))
                image_bb = [person_bboxes[idx] for idx in person_alert_indices]
        
        elif detection_type.lower() == "objects" and detections:
            # Process object-based alerts (weapons, face coverings, etc.)
            try:
                detections_list = json.loads(detections)
                logger.debug(f"Parsed {len(detections_list)} detections from JSON")
                
                # Analyze detections
                alert_indices, alert_types = analyze_detections(detections_list)
                
                # Collect alert types
                all_alert_types = set()
                for idx in alert_indices:
                    if idx in alert_types:
                        all_alert_types.update(alert_types[idx])
                
                result_alerts = list(all_alert_types)
                
                if alert_indices:
                    logger.info(f"Alerts detected: {', '.join(result_alerts)}")
                    
                    # Draw bounding boxes for alerted objects
                    detection_bboxes = get_detection_bboxes(detections_list)
                    base_img = draw_detection_boxes(base_img, detections_list, alert_indices, alert_types)
                    
                    # Collect bounding boxes for response
                    image_bb = [detections_list[idx]["bbox"] for idx in alert_indices]
            except Exception as e:
                logger.error(f"Error processing detections: {str(e)}")
                return JSONResponse(content={
                    "error": f"Error processing detections: {str(e)}"
                }, status_code=500)
        
        else:
            logger.warning(f"Unsupported detection type: {detection_type}")
            result_alerts = ["Unknown_Detection_Type"]

        # Save overlay and keep images if we have alerts
        saved_overlay_path = None
        alert_filename = None
        if result_alerts and result_alerts != ["Unknown_Detection_Type"] and base_img is not None and base_img.size > 0:
            try:
                # Create timestamp-based filename for alert
                alert_type_str = '_'.join(result_alerts)
                timestamp = datetime.now(india_tz).strftime("%H%M%S")
                alert_filename = f"alert_{camera_id}_{timestamp}_{alert_type_str}.jpg"
                alert_path = os.path.join(OUTPUT_DIR, alert_filename)
                
                # Debug the UUID issue
                logger.warning(f"DEBUGGING UUID ISSUE: Before saving, alert_filename={alert_filename}, path={alert_path}")
                
                # Save both overlay and alert images to appropriate paths
                saved_overlay_path = alert_path  # Use the same path for both alert and overlay
                
                # This is critical - we never generate alertoverlay_ files anymore
                logger.info(f"Alert image will be saved with standardized name: {alert_filename}")
                
                logger.debug(f"Saving overlay image to {saved_overlay_path}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(saved_overlay_path)), exist_ok=True)
                
                # Check if there's an alertoverlay file with a similar name
                alertoverlay_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('alertoverlay_')]
                if alertoverlay_files:
                    logger.warning(f"FOUND EXISTING ALERTOVERLAY FILES: {alertoverlay_files}")
                
                success = cv2.imwrite(saved_overlay_path, base_img)
                
                # Check again after writing our file if any alertoverlay file was created
                logger.warning(f"CHECKING FOR UUID-BASED FILES AFTER SAVING OUR STANDARDIZED FILE")
                new_alertoverlay_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('alertoverlay_')]
                if new_alertoverlay_files != alertoverlay_files:
                    logger.error(f"NEW ALERTOVERLAY FILES DETECTED: {set(new_alertoverlay_files) - set(alertoverlay_files)}")
                
                if not success or not os.path.exists(saved_overlay_path):
                    logger.error(f"Failed to save overlay image to {saved_overlay_path}")
                    saved_overlay_path = None
                else:
                    if os.path.getsize(saved_overlay_path) > 0:
                        logger.debug(f"Successfully saved overlay to {saved_overlay_path}")
                    else:
                        logger.error(f"Overlay file is empty: {saved_overlay_path}")
                        saved_overlay_path = None
            except Exception as e:
                logger.error(f"Error saving overlay: {str(e)}")
                logger.exception("Detailed overlay save exception:")
                saved_overlay_path = None
        else:
            if not result_alerts:
                logger.debug("No alerts detected - deleting source and overlay images")
                
                try:
                    # Delete source image
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logger.info(f"Deleted source image: {image_path}")
                    
                    # Delete overlay image if it exists
                    if image_overlay and os.path.exists(image_overlay):
                        os.remove(image_overlay)
                        logger.info(f"Deleted overlay image: {image_overlay}")
                except Exception as e:
                    logger.error(f"Error deleting unused images: {str(e)}")
                    logger.exception("Detailed image deletion exception:")
            elif base_img is None or base_img.size == 0:
                logger.error("Cannot save overlay: base_img is None or empty")

        response_data = {
            "type_of_alert": ",".join(result_alerts) if result_alerts else "No_Alert",
            "SourceID": camera_id,
            "Detection_type": detection_type,
            "date_Time": date_time,
            "Image_source": image_path,
            "Image_overlay": saved_overlay_path,
            "Image_bb": image_bb if image_bb else None
        }
        
        # Save alert to database if it's a real alert (not "No_Alert")
        if result_alerts and result_alerts != ["Unknown_Detection_Type"]:
            try:
                alert_repo = AlertRepository()
                # Create joined alert type string for consistent naming
                alert_type_str = '_'.join(result_alerts)
                alert_data = {
                    "camera_id": camera_id,
                    "alert_type": alert_type_str,  # Using full combined alert type
                    "datetime": datetime.now(india_tz) if "T" not in date_time else datetime.fromisoformat(date_time),
                    "source_image_path": image_path,
                    "overlay_image_path": saved_overlay_path,
                    "alert_image_path": saved_overlay_path,  # Use the same saved overlay path
                    "persons_count": len(person_alert_indices) if 'person_alert_indices' in locals() and person_alert_indices else 0,
                    "details": json.dumps({
                        "detection_type": detection_type,
                        "alert_name": alert_filename,  # Include the alert filename in details
                        "image_bb": image_bb if image_bb else []
                    })
                }
                alert_id = alert_repo.create_alert(alert_data)
                logger.info(f"Alert saved to database with ID: {alert_id}")
                response_data["alert_id"] = alert_id
            except Exception as e:
                logger.error(f"Error saving alert to database: {str(e)}")
                logger.exception("Database error details:")
        
        # Final check for alertoverlay files at the end of processing
        logger.warning(f"FINAL CHECK FOR ALERTOVERLAY FILES")
        final_alertoverlay_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('alertoverlay_')]
        if final_alertoverlay_files:
            logger.error(f"ALERTOVERLAY FILES AT END OF PROCESSING: {final_alertoverlay_files}")
        
        # Final check for alertoverlay files - rename any that still exist
        alertoverlay_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('alertoverlay_')]
        if alertoverlay_files:
            logger.warning(f"Found {len(alertoverlay_files)} alertoverlay files at end of processing - renaming them")
            for alertoverlay_file in alertoverlay_files:
                try:
                    old_path = os.path.join(OUTPUT_DIR, alertoverlay_file)
                    
                    # Create a standardized name
                    timestamp = datetime.now(india_tz).strftime("%H%M%S")
                    new_filename = f"alert_{camera_id}_{timestamp}_Fixed.jpg"
                    new_path = os.path.join(OUTPUT_DIR, new_filename)
                    
                    # Rename the file
                    os.rename(old_path, new_path)
                    logger.warning(f"Renamed {alertoverlay_file} to {new_filename}")
                except Exception as e:
                    logger.error(f"Error renaming {alertoverlay_file}: {str(e)}")
        
        logger.info(f"Alert processing completed for camera {camera_id}")
        return JSONResponse(content=response_data)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in input data: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(content={
            "error": error_msg
        }, status_code=400)
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error(error_msg)
        logger.exception("Detailed exception information:")
        return JSONResponse(content={
            "error": error_msg,
            "path_checked": image_source if 'image_source' in locals() else None
        }, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Ensure output directory exists and is writable
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        test_file = os.path.join(OUTPUT_DIR, ".health_check")
        with open(test_file, "w") as f:
            f.write("OK")
        os.remove(test_file)
        return {"status": "healthy", "output_dir_writable": True}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=500
        )

# Background cleanup task
def periodic_cleanup(interval_minutes=60, min_age_minutes=30):
    """Run cleanup task periodically"""
    while True:
        try:
            time.sleep(interval_minutes * 60)  # Convert minutes to seconds
            logger.info(f"Starting scheduled cleanup (runs every {interval_minutes} minutes)")
            cleaner = ImageCleaner(OUTPUT_DIR, min_age_minutes)
            deleted_count = cleaner.cleanup(dry_run=False)
            logger.info(f"Scheduled cleanup completed: {deleted_count} files deleted")
        except Exception as e:
            logger.error(f"Error in scheduled cleanup: {str(e)}")
            logger.exception("Detailed cleanup exception:")

# Start the background cleanup thread
cleanup_thread = threading.Thread(
    target=periodic_cleanup, 
    args=(60, 30),  # Run every 60 minutes, clean files older than 30 minutes
    daemon=True
)
cleanup_thread.start()
logger.info("Background image cleanup task started")

@app.post("/cleanup")
async def trigger_cleanup(min_age_minutes: int = 30, dry_run: bool = False):
    """Manually trigger cleanup of unused images"""
    try:
        logger.info(f"Manual cleanup triggered: min_age_minutes={min_age_minutes}, dry_run={dry_run}")
        cleaner = ImageCleaner(OUTPUT_DIR, min_age_minutes)
        deleted_count = cleaner.cleanup(dry_run)
        
        return {
            "status": "success",
            "message": f"Cleanup {'simulation' if dry_run else 'operation'} completed",
            "deleted_count": deleted_count,
            "dry_run": dry_run
        }
    except Exception as e:
        error_msg = f"Cleanup error: {str(e)}"
        logger.error(error_msg)
        logger.exception("Detailed exception information:")
        return JSONResponse(
            content={"status": "error", "error": error_msg},
            status_code=500
        )

@app.get("/alerts")
async def get_alerts(
    limit: int = 100, 
    offset: int = 0, 
    camera_id: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    alert_type: str = None
):
    """Get alerts with filtering options"""
    try:
        alert_repo = AlertRepository()
        
        # Parse date strings if provided
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    content={"error": f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    status_code=400
                )
        
        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    content={"error": f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    status_code=400
                )
        
        alerts = alert_repo.get_alerts(
            limit=limit,
            offset=offset,
            camera_id=camera_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            alert_type=alert_type
        )
        
        return {
            "total": len(alerts),
            "offset": offset,
            "limit": limit,
            "alerts": alerts
        }
    except Exception as e:
        error_msg = f"Error fetching alerts: {str(e)}"
        logger.error(error_msg)
        logger.exception("Detailed exception information:")
        return JSONResponse(
            content={"status": "error", "error": error_msg},
            status_code=500
        )

@app.get("/alerts/{alert_id}")
async def get_alert_by_id(alert_id: int):
    """Get a specific alert by ID"""
    try:
        alert_repo = AlertRepository()
        alert = alert_repo.get_alert_by_id(alert_id)
        
        if not alert:
            return JSONResponse(
                content={"error": f"Alert with ID {alert_id} not found"},
                status_code=404
            )
        
        return alert
    except Exception as e:
        error_msg = f"Error fetching alert {alert_id}: {str(e)}"
        logger.error(error_msg)
        logger.exception("Detailed exception information:")
        return JSONResponse(
            content={"status": "error", "error": error_msg},
            status_code=500
        )
