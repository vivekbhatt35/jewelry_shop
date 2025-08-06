import os
import cv2
import shutil
import numpy as np
from datetime import datetime
import pytz
import asyncio
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from ultralytics import YOLO
import requests
import json
from utils.logger import setup_logger

# Set up logger
logger = setup_logger("Detector-Detections")

# Define India timezone
india_tz = pytz.timezone('Asia/Kolkata')

app = FastAPI()

MODEL_FOLDER = "models"
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output_image')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)  # Ensure model folder exists

# Update alert service URL to use environment variable
ALERT_SERVICE_URL = os.getenv('ALERT_SERVICE_URL', 'http://alert-logic:8012/alert')

# Define classes of interest
CLASSES_OF_INTEREST = [
    "person", "knife", "scissors", "gun", "pistol", "rifle", "mask", "helmet", "backpack"
]

# Global model variable
model = None

def load_model():
    """Load YOLO model safely with fallback options"""
    global model
    try:
        # First try to find a model in the models folder
        model_path = get_model_path(MODEL_FOLDER)
        if model_path:
            logger.info(f"Loading detection model from {model_path}")
            model = YOLO(model_path)
            logger.info("Detection model loaded successfully")
            return True
            
        # If no local model, try downloading a small one
        logger.warning("No .pt model file found in models/ directory. Downloading default model...")
        model = YOLO("yolov8n.pt")  # Downloading the smallest YOLOv8 model
        
        # Save the downloaded model to models directory for future use
        if hasattr(model, 'ckpt_path'):
            dest_path = os.path.join(MODEL_FOLDER, "yolov8n.pt")
            shutil.copy2(model.ckpt_path, dest_path)
            logger.info(f"Saved downloaded model to {dest_path}")
            
        logger.info("Downloaded and loaded default model successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        return False

def get_model_path(model_folder):
    """Get the path to the YOLO model file"""
    if not os.path.exists(model_folder):
        os.makedirs(model_folder, exist_ok=True)
        return None
        
    for fname in os.listdir(model_folder):
        if fname.endswith(".pt") and "yolo" in fname.lower():
            return os.path.join(model_folder, fname)
    return None

# Try to load the model at startup but don't fail if it can't be loaded
try:
    load_model()
except Exception as e:
    logger.error(f"Error during model loading: {str(e)}")
    logger.info("Service will start without model and attempt to load it when needed")

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies if the model is loaded"""
    if model is None:
        # Try loading the model if it's not loaded yet
        if not load_model():
            return JSONResponse(content={"status": "degraded", "message": "Model not loaded, but service is running"}, status_code=200)
    
    return {"status": "healthy", "model_loaded": model is not None}

@app.post("/detect/image")
async def detect_from_image(
    file: UploadFile = File(...),
    output_image: int = Form(0),
    camera_id: str = Form(...)
):
    # Check if model is loaded
    if model is None:
        if not load_model():
            logger.warning("Model not loaded, attempting to proceed with fallback options")
            # Continue with empty detections rather than failing completely
            return JSONResponse(content={
                "camera_id": camera_id,
                "timestamp": datetime.now(india_tz).isoformat(),
                "detections": [],
                "source_image": None,
                "error": "Model not available"
            })
    
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
        logger.debug("YOLO detection completed")
    except Exception as e:
        logger.error(f"Error during YOLO detection: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(content={
            "error": f"Error during YOLO detection: {str(e)}"
        }, status_code=500)
    
    detections = []
    overlay_img = img.copy()
    
    # Process the results
    result = results[0]
    
    if hasattr(result, "boxes") and len(result.boxes) > 0:
        boxes = result.boxes
        for i, box in enumerate(boxes):
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Get class info
            cls_id = int(box.cls[0].item())
            cls_name = result.names[cls_id]
            conf = float(box.conf[0].item())
            
            # Check if this is a class we're interested in
            if cls_name.lower() in [c.lower() for c in CLASSES_OF_INTEREST]:
                logger.info(f"Detected {cls_name} with confidence {conf:.2f}")
                
                # Add to detections list
                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
                
                # Draw on overlay image
                if output_image == 1:
                    color = (0, 255, 0)  # Green for general objects
                    if cls_name.lower() in ["gun", "knife", "scissors", "pistol", "rifle"]:
                        color = (0, 0, 255)  # Red for weapons
                    elif cls_name.lower() in ["mask", "helmet"]:
                        color = (255, 0, 0)  # Blue for face coverings
                        
                    cv2.rectangle(overlay_img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(overlay_img, f"{cls_name} {conf:.2f}", 
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # If no objects of interest detected
    if not detections:
        logger.info("No objects of interest detected")
    else:
        logger.info(f"Detected {len(detections)} objects of interest")
    
    overlay_path = None
    if output_image == 1:
        overlay_name = f"overlay_{base_filename}"
        overlay_path = os.path.join(OUTPUT_DIR, overlay_name)
        cv2.imwrite(overlay_path, overlay_img)
        logger.debug(f"Saved overlay image to {overlay_path}")

    # Cleanup temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # Prepare response
    response = {
        "camera_id": camera_id,
        "timestamp": datetime.now(india_tz).isoformat(),
        "detections": detections,
        "source_image": source_path
    }
    if overlay_path:
        response["overlay_image_path"] = overlay_path

    # Forward to alert service only if we have detections
    if detections:
        try:
            # Verify the image files exist before sending
            if not os.path.exists(source_path):
                logger.warning(f"Source image doesn't exist: {source_path}")
            
            if overlay_path and not os.path.exists(overlay_path):
                logger.warning(f"Overlay image doesn't exist: {overlay_path}")
                
            # Make sure paths are correctly formatted
            alert_payload = {
                "camera_id": camera_id,
                "detection_type": "objects",
                "date_time": response["timestamp"],
                "image_source": source_path,
                "image_overlay": overlay_path if overlay_path else None,
                "detections": json.dumps(detections)
            }
            
            logger.debug(f"Sending request to alert service: {ALERT_SERVICE_URL}")
            logger.debug(f"Alert payload image paths: source={source_path}, overlay={overlay_path}")
            
            alert_response = requests.post(
                ALERT_SERVICE_URL,
                data=alert_payload,
                timeout=10
            )
            
            if alert_response.status_code != 200:
                logger.warning(f"Alert service returned non-200 status: {alert_response.status_code}")
                logger.warning(f"Response content: {alert_response.text[:1000]}")
                response["alert_status"] = {"warning": f"Non-200 status: {alert_response.status_code}"}
            else:
                response["alert_status"] = alert_response.json()
                logger.info("Alert service response received successfully")
        except Exception as e:
            error_msg = f"Alert service error: {str(e)}"
            response["alert_status"] = {"error": error_msg}
            logger.error(error_msg)
            logger.exception("Details:")

    # Single return statement
    return JSONResponse(content=response)
