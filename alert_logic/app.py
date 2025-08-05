from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from logic.pose_analysis import hands_up_detect, get_person_bboxes, draw_bboxes
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
    poses: str = Form(...)
):
    try:
        logger.info(f"Processing alert from camera {camera_id}")
        poses_list = json.loads(poses)
        
        # Convert to relative path
        image_source = os.path.join(OUTPUT_DIR, os.path.basename(image_source))
        logger.debug(f"Looking for source image at: {image_source}")
        
        # Ensure image path exists and is readable
        if not os.path.exists(image_source):
            error_msg = f"Image not found: {image_source}"
            logger.error(error_msg)
            return JSONResponse(content={
                "error": error_msg,
                "path_checked": image_source
            }, status_code=400)

        base_img = cv2.imread(image_source)
        if base_img is None:
            error_msg = f"Failed to load image: {image_source}"
            logger.error(error_msg)
            return JSONResponse(content={
                "error": error_msg,
                "path_checked": image_source
            }, status_code=400)
        
        logger.debug("Image loaded successfully")

        # Analyze for hands up
        person_alert_indices = hands_up_detect(poses_list)
        result_alerts = ["Hands_Up"] if person_alert_indices else []
        
        if result_alerts:
            logger.info(f"Alert detected: {', '.join(result_alerts)} for persons {person_alert_indices}")
        else:
            logger.info("No alerts detected")

        # Draw bounding boxes for alerted persons
        image_bb = []
        if person_alert_indices:
            person_bboxes = get_person_bboxes(poses_list)
            base_img = draw_bboxes(base_img, person_bboxes, person_alert_indices, color=(0, 0, 255))
            image_bb = [person_bboxes[idx] for idx in person_alert_indices]
            logger.debug(f"Drew bounding boxes for {len(person_alert_indices)} persons")

        # Save new overlay if we have alerts
        saved_overlay_path = None
        if result_alerts:
            unique_id = str(uuid.uuid4())
            file_name = f"alertoverlay_{unique_id}.jpg"
            saved_overlay_path = os.path.join(OUTPUT_DIR, file_name)
            cv2.imwrite(saved_overlay_path, base_img)
            logger.debug(f"Saved alert overlay to {saved_overlay_path}")

        response_data = {
            "type_of_alert": ",".join(result_alerts) if result_alerts else "No_Alert",
            "SourceID": camera_id,
            "Detection_type": detection_type,
            "date_Time": date_time,
            "Image_source": image_source,
            "Image_overlay": saved_overlay_path,
            "Image_bb": image_bb if image_bb else None
        }
        
        logger.info(f"Alert processing completed for camera {camera_id}")
        return JSONResponse(content=response_data)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in poses data: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(content={
            "error": error_msg
        }, status_code=400)
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(content={
            "error": error_msg,
            "path_checked": image_source if 'image_source' in locals() else None
        }, status_code=500)
