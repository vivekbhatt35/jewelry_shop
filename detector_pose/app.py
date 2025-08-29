import os
import cv2
import shutil
import numpy as np
from datetime import datetime
import pytz
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from ultralytics import YOLO
import requests
import json
from utils.logger import setup_logger

# Set up logger
logger = setup_logger("Detector-Pose")

# Define India timezone
india_tz = pytz.timezone('Asia/Kolkata')

app = FastAPI()

MODEL_FOLDER = "models"
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output_image')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Update alert service URL to use environment variable
ALERT_SERVICE_URL = os.getenv('ALERT_SERVICE_URL', 'http://alert-logic:8012/alert')

def get_model_path(model_folder):
    for fname in os.listdir(model_folder):
        if fname.endswith(".pt"):
            return os.path.join(model_folder, fname)
    return None

model_path = get_model_path(MODEL_FOLDER)
if model_path is None:
    logger.error("No .pt model file found in models/ directory.")
    raise RuntimeError("No .pt model file found in models/ directory.")

logger.info(f"Loading model from {model_path}")
model = YOLO(model_path)
logger.info("Model loaded successfully")

@app.post("/pose/image")
async def pose_from_image(
    file: UploadFile = File(...),
    output_image: int = Form(0),
    camera_id: str = Form(...),
    metadata: str = Form(None)
):
    logger.info(f"Processing image from camera {camera_id}")
    
    # Create a timestamp-based filename with India timezone
    timestamp = datetime.now(india_tz).strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1]
    base_filename = f"{timestamp}_{camera_id}{file_ext}"
    
    # Use relative paths with OUTPUT_DIR
    source_path = os.path.join(OUTPUT_DIR, f"source_{base_filename}")
    temp_path = os.path.join(OUTPUT_DIR, f"temp_{base_filename}")
    
    # Save uploaded file
    try:
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
        logger.debug(f"Saved temporary file to {temp_path}")
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}")
        return JSONResponse(content={
            "error": f"Error saving uploaded file: {str(e)}"
        }, status_code=500)
    
    # Read and process image
    img = cv2.imread(temp_path)
    if img is None:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Failed to read uploaded image at {temp_path}")
        return JSONResponse(content={
            "error": "Failed to read uploaded image",
            "path_checked": temp_path
        }, status_code=400)

    # Save source image first for alert service
    cv2.imwrite(source_path, img)
    logger.debug(f"Saved source image to {source_path}")
    
    # Process image with YOLO
    try:
        results = model(img)
        logger.debug("YOLO processing completed")
    except Exception as e:
        logger.error(f"Error during YOLO processing: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(content={
            "error": f"Error during YOLO processing: {str(e)}"
        }, status_code=500)
    
    poses = []
    overlay_img = img.copy()

    keypoints_result = getattr(results[0], "keypoints", None)
    if (keypoints_result is not None) and hasattr(keypoints_result, "data"):
        # Usually shape: (num_persons, num_keypoints, values_per_keypoint)
        kp_data = keypoints_result.data.cpu().numpy()
        for person_kps in kp_data:
            # person_kps: shape (num_keypoints, values_per_keypoint)
            # Use only first three elements: x, y, [v] (visibility or conf)
            for keypoint in person_kps:
                # Defensive: convert to 3 elements, or fill v=1 if missing
                x = keypoint[0]
                y = keypoint[1]
                v = keypoint[2] if len(keypoint) > 2 else 1  # sometimes no v/conf
                # Now v is a scalar, guaranteed
                try:
                    v_value = float(v)
                except Exception:
                    v_value = 1
                if v_value > 0:
                    cv2.circle(overlay_img, (int(x), int(y)), 4, (0, 255, 0), -1)
            poses.append(person_kps[:, :3].astype(int).flatten().tolist())
        
        logger.info(f"Detected {len(poses)} persons in image")
    else:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.info("No keypoints found in image")
        return JSONResponse(content={
            "error": "No keypoints found in image.",
            "poses": [],
            "overlay_image_path": None
        }, status_code=200)

    overlay_path = None
    if output_image == 1:
        overlay_name = f"overlay_{base_filename}"
        overlay_path = os.path.join(OUTPUT_DIR, overlay_name)
        cv2.imwrite(overlay_path, overlay_img)
        logger.debug(f"Saved overlay image to {overlay_path}")

    # Cleanup temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # Use India timezone in response
    response = {
        "camera_id": camera_id,
        "timestamp": datetime.now(india_tz).isoformat(),
        "poses": poses,
        "source_image": source_path
    }
    if overlay_path:
        response["overlay_image_path"] = overlay_path

    # Forward to alert service
    try:
        alert_payload = {
            "camera_id": camera_id,
            "detection_type": "poses",
            "date_time": response["timestamp"],
            "image_source": source_path,
            "image_overlay": overlay_path if overlay_path else None,
            "poses": json.dumps(poses)
        }
        
        # Pass metadata if available
        if metadata:
            alert_payload["metadata"] = metadata
            logger.debug(f"Passing metadata to alert service: {metadata}")
        
        logger.debug(f"Sending request to alert service: {ALERT_SERVICE_URL}")
        alert_response = requests.post(
            ALERT_SERVICE_URL,
            data=alert_payload,
            timeout=10
        )
        
        # Get the response from the alert service
        alert_result = alert_response.json()
        response["alert_status"] = alert_result
        
        # Check if an alert was generated
        alert_type = alert_result.get("type_of_alert", "No_Alert")
        if alert_type == "No_Alert":
            # No alert was generated, delete the source and overlay images to save disk space
            logger.info("No alert generated, deleting source and overlay images")
            try:
                # Delete source image
                if os.path.exists(source_path):
                    os.remove(source_path)
                    logger.info(f"Deleted source image: {source_path}")
                
                # Delete overlay image if it exists
                if overlay_path and os.path.exists(overlay_path):
                    os.remove(overlay_path)
                    logger.info(f"Deleted overlay image: {overlay_path}")
            except Exception as e:
                logger.error(f"Error deleting unused images: {str(e)}")
        else:
            logger.info(f"Alert generated: {alert_type}, keeping images")
    except Exception as e:
        error_msg = f"Alert service error: {str(e)}"
        response["alert_status"] = {"error": error_msg}
        logger.error(error_msg)

    return JSONResponse(content=response)
