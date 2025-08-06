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
from utils.logger import setup_logger

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

        # Save new overlay if we have alerts and base_img is valid
        saved_overlay_path = None
        if result_alerts and result_alerts != ["Unknown_Detection_Type"] and base_img is not None and base_img.size > 0:
            try:
                unique_id = str(uuid.uuid4())
                file_name = f"alertoverlay_{unique_id}.jpg"
                saved_overlay_path = os.path.join(OUTPUT_DIR, file_name)
                
                logger.debug(f"Saving overlay image to {saved_overlay_path}, image shape: {base_img.shape}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(saved_overlay_path)), exist_ok=True)
                
                success = cv2.imwrite(saved_overlay_path, base_img)
                
                if not success or not os.path.exists(saved_overlay_path):
                    logger.error(f"Failed to save overlay image to {saved_overlay_path}")
                    saved_overlay_path = None
                else:
                    # Verify the saved file
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
                logger.debug("No alerts to save overlay for")
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
