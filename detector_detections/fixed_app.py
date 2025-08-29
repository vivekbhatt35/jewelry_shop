import os
import cv2
import shutil
import numpy as np
from datetime import datetime
import pytz
import asyncio
import time
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
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

# Constants
MODEL_FOLDER = "models"
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output_image')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Update alert service URL to use environment variable
ALERT_SERVICE_URL = os.getenv('ALERT_SERVICE_URL', 'http://alert-logic:8012/alert')

# Define classes of interest based on our trained model
# Model trained with classes: 0-person, 1-weapon, 2-suspicious, 3-helmet, 4-mask
CLASSES_OF_INTEREST = [
    "person", "weapon", "suspicious", "helmet", "mask"
]

# Detection confidence thresholds by class
CONFIDENCE_THRESHOLDS = {
    "person": 0.45,     # Higher threshold for common class
    "weapon": 0.15,     # Very low threshold for critical class
    "suspicious": 0.25, # Low threshold for suspicious behavior
    "helmet": 0.35,     # Medium threshold
    "mask": 0.35        # Medium threshold
}

# Global variables
model = None

def get_model_path(model_folder):
    for fname in os.listdir(model_folder):
        if fname.endswith(".pt"):
            return os.path.join(model_folder, fname)
    return None

def load_model():
    """Load YOLO model safely with fallback options"""
    global model
    try:
        # Use regular model path logic to find best.pt
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
            
        logger.info("Default model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        logger.exception("Model loading error details:")
        return False

# Try to load model at startup
try:
    if not load_model():
        logger.warning("Failed to load model at startup, will retry on first request")
except Exception as e:
    logger.error(f"Error during startup model loading: {str(e)}")

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
                    # Color mapping for our new class structure
                    # 0-person: green, 1-weapon: red, 2-suspicious: orange, 3-helmet/4-mask: blue
                    color_map = {
                        "person": (0, 255, 0),     # Green for person
                        "weapon": (0, 0, 255),     # Red for weapons
                        "suspicious": (0, 165, 255),  # Orange for suspicious
                        "helmet": (255, 0, 0),     # Blue for helmet
                        "mask": (255, 0, 0)        # Blue for mask
                    }
                    
                    # Get color based on class name or default to green
                    color = color_map.get(cls_name.lower(), (0, 255, 0))
                        
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
            
            # Implement retry logic for connecting to the alert service
            max_retries = 3
            retry_delay = 2  # seconds
            
            for retry in range(max_retries):
                try:
                    alert_response = requests.post(
                        ALERT_SERVICE_URL,
                        data=alert_payload,
                        timeout=10
                    )
                    # If successful, break out of the retry loop
                    break
                except requests.exceptions.RequestException as e:
                    if retry < max_retries - 1:
                        logger.warning(f"Failed to connect to alert service (attempt {retry+1}/{max_retries}): {str(e)}")
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Failed to connect to alert service after {max_retries} attempts: {str(e)}")
                        logger.exception("Alert service connection error details:")
            
            # Include alert response in the API response
            try:
                response["alert_status"] = alert_response.json()
            except Exception as alert_parse_error:
                logger.warning(f"Failed to parse alert response: {str(alert_parse_error)}")
                response["alert_status"] = {"status": "error", "message": "Failed to parse alert service response"}
            
        except Exception as e:
            logger.error(f"Error forwarding to alert service: {str(e)}")
            logger.exception("Alert forwarding error details:")
            response["alert_status"] = {"status": "error", "message": str(e)}

    return response

@app.post("/camera_frame")
async def process_camera_frame(
    request: Request,
    camera_id: str = Form(...),
    timestamp: str = Form(...),
    frame_id: str = Form(None)
):
    """
    Process a frame from the camera manager service.
    This endpoint is designed to be called by the camera_manager service.
    """
    try:
        # Check if model is loaded
        if model is None and not load_model():
            logger.warning("Model not loaded, cannot process frame")
            return JSONResponse(content={
                "camera_id": camera_id,
                "timestamp": timestamp,
                "status": "error",
                "message": "Detection model not available"
            }, status_code=500)
        
        form = await request.form()
        frame_file = form.get("frame")
        
        if not frame_file:
            logger.error("No frame file provided in request")
            return JSONResponse(content={
                "camera_id": camera_id,
                "status": "error",
                "message": "No frame file provided"
            }, status_code=400)
        
        # Create unique filename
        frame_id = frame_id or str(uuid.uuid4())[:8]
        timestamp_formatted = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime("%Y%m%d_%H%M%S") if 'T' in timestamp else timestamp
        base_filename = f"{timestamp_formatted}_{camera_id}_{frame_id}.jpg"
        temp_path = os.path.join(OUTPUT_DIR, f"temp_{base_filename}")
        source_path = os.path.join(OUTPUT_DIR, f"source_{base_filename}")
        
        # Save the uploaded frame
        contents = await frame_file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # Process image
        img = cv2.imread(temp_path)
        if img is None:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Failed to read frame image at {temp_path}")
            return JSONResponse(content={
                "status": "error",
                "message": "Failed to read frame image"
            }, status_code=400)
        
        # Save source image for alert service
        cv2.imwrite(source_path, img)
        
        # Run inference
        results = model(img)
        
        # Process results
        detections = []
        overlay_img = img.copy()
        
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
                
                # Apply class-specific confidence thresholds
                threshold = CONFIDENCE_THRESHOLDS.get(cls_name.lower(), 0.35)
                if conf < threshold:
                    continue
                
                # Process detection if it's a class we're interested in
                if cls_name.lower() in [c.lower() for c in CLASSES_OF_INTEREST]:
                    logger.info(f"Detected {cls_name} in camera {camera_id} with confidence {conf:.2f}")
                    
                    # Add to detections
                    detections.append({
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2]
                    })
                    
                    # Color mapping for visualization
                    color_map = {
                        "person": (0, 255, 0),     # Green for person
                        "weapon": (0, 0, 255),     # Red for weapons
                        "suspicious": (0, 165, 255),  # Orange for suspicious
                        "helmet": (255, 0, 0),     # Blue for helmet
                        "mask": (255, 0, 0)        # Blue for mask
                    }
                    color = color_map.get(cls_name.lower(), (0, 255, 0))
                    
                    # Draw bounding box
                    cv2.rectangle(overlay_img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(overlay_img, f"{cls_name} {conf:.2f}", 
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Save overlay image
        overlay_path = os.path.join(OUTPUT_DIR, f"overlay_{base_filename}")
        cv2.imwrite(overlay_path, overlay_img)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Prepare response
        response = {
            "camera_id": camera_id,
            "timestamp": timestamp,
            "frame_id": frame_id,
            "detections": detections,
            "source_image": source_path,
            "overlay_image": overlay_path
        }
        
        # Forward to alert service if there are detections
        if detections:
            try:
                alert_payload = {
                    "camera_id": camera_id,
                    "detection_type": "objects",
                    "date_time": timestamp,
                    "image_source": source_path,
                    "image_overlay": overlay_path,
                    "detections": json.dumps(detections)
                }
                
                # Send to alert service with retry logic
                max_retries = 3
                retry_delay = 1
                
                for retry in range(max_retries):
                    try:
                        alert_response = requests.post(
                            ALERT_SERVICE_URL,
                            data=alert_payload,
                            timeout=5
                        )
                        break
                    except requests.exceptions.RequestException as e:
                        if retry < max_retries - 1:
                            logger.warning(f"Alert service connection failed (attempt {retry+1}): {str(e)}")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            logger.error(f"Failed to connect to alert service: {str(e)}")
                
                # Include alert response
                try:
                    response["alert_status"] = alert_response.json()
                except Exception as e:
                    logger.warning(f"Failed to parse alert response: {str(e)}")
                    response["alert_status"] = {"status": "unknown"}
                
            except Exception as e:
                logger.error(f"Error forwarding to alert service: {str(e)}")
                response["alert_status"] = {"status": "error", "message": str(e)}
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing camera frame: {str(e)}")
        logger.exception("Details:")
        return JSONResponse(content={
            "camera_id": camera_id,
            "status": "error",
            "message": f"Internal error: {str(e)}"
        }, status_code=500)

@app.get("/model/classes")
async def get_model_classes():
    """
    Get the classes supported by the loaded detection model.
    This endpoint returns all available classes in the model as well as the subset of classes of interest.
    """
    # Check if model is loaded
    if model is None:
        if not load_model():
            logger.warning("Failed to load model for class information")
            return JSONResponse(content={
                "status": "error",
                "message": "Model not available",
                "classes_of_interest": CLASSES_OF_INTEREST
            }, status_code=500)
    
    try:
        # Get the names dictionary from the model
        if hasattr(model, 'names'):
            all_classes = model.names
            
            # Convert the names dictionary to a more readable format
            # The names dict has integer keys and string values
            available_classes = {str(k): v for k, v in all_classes.items()}
            
            return {
                "status": "success",
                "model_path": model.ckpt_path if hasattr(model, 'ckpt_path') else "Unknown",
                "all_classes": available_classes,
                "classes_of_interest": CLASSES_OF_INTEREST,
                "confidence_thresholds": CONFIDENCE_THRESHOLDS
            }
        else:
            logger.warning("Model doesn't have 'names' attribute")
            return JSONResponse(content={
                "status": "error",
                "message": "Model doesn't have class information",
                "classes_of_interest": CLASSES_OF_INTEREST
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error retrieving model classes: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Error retrieving model classes: {str(e)}",
            "classes_of_interest": CLASSES_OF_INTEREST
        }, status_code=500)

@app.post("/detect/raw")
async def detect_raw_output(
    file: UploadFile = File(...),
    conf: float = Form(0.1)  # Lower default confidence threshold to capture more detections
):
    """
    Process an image with the YOLO model and return the raw detection results.
    This endpoint returns all detections from the model without any filtering or post-processing.
    """
    # Check if model is loaded
    if model is None:
        if not load_model():
            logger.warning("Model not loaded, cannot process image")
            return JSONResponse(content={
                "status": "error",
                "message": "Model not available"
            }, status_code=500)
    
    try:
        # Save uploaded file to temp location
        temp_path = os.path.join(OUTPUT_DIR, f"raw_temp_{uuid.uuid4()}.jpg")
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # Read and process image
        img = cv2.imread(temp_path)
        if img is None:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return JSONResponse(content={
                "error": "Failed to read uploaded image",
                "path_checked": temp_path
            }, status_code=400)
        
        # Process with YOLO using provided confidence threshold
        results = model(img, conf=conf)
        result = results[0]
        
        # Extract all detections
        all_detections = []
        
        if hasattr(result, "boxes") and len(result.boxes) > 0:
            boxes = result.boxes
            for i, box in enumerate(boxes):
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Get class info
                cls_id = int(box.cls[0].item())
                cls_name = result.names[cls_id]
                conf = float(box.conf[0].item())
                
                all_detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": conf,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                })
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {
            "status": "success",
            "timestamp": datetime.now(india_tz).isoformat(),
            "all_detections": all_detections,
            "model_name": model.ckpt_path if hasattr(model, 'ckpt_path') else "Unknown",
            "input_shape": img.shape
        }
    except Exception as e:
        logger.error(f"Error in raw detection: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(content={
            "status": "error",
            "message": f"Error in raw detection: {str(e)}"
        }, status_code=500)

@app.post("/detect/all")
async def detect_all_classes(
    file: UploadFile = File(...),
    min_conf: float = Form(0.01),  # Lower minimum confidence threshold
    camera_id: str = Form("TEST_CAM"),
    output_image: int = Form(1)  # Default to generating overlay image
):
    """
    Process an image with the YOLO model and return detections for ALL classes,
    regardless of the classes of interest filter, with configurable confidence threshold.
    Also generates an overlay image with ALL detections.
    """
    # Check if model is loaded
    if model is None:
        if not load_model():
            logger.warning("Model not loaded, cannot process image")
            return JSONResponse(content={
                "status": "error",
                "message": "Model not available"
            }, status_code=500)
    
    try:
        # Create a timestamp-based filename
        timestamp = datetime.now(india_tz).strftime("%Y%m%d_%H%M%S")
        file_ext = os.path.splitext(file.filename)[1]
        base_filename = f"{timestamp}_all_{camera_id}{file_ext}"
        
        # Define file paths
        temp_path = os.path.join(OUTPUT_DIR, f"temp_{base_filename}")
        source_path = os.path.join(OUTPUT_DIR, f"source_{base_filename}")
        
        # Save uploaded file
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # Read and process image
        img = cv2.imread(temp_path)
        if img is None:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return JSONResponse(content={
                "error": "Failed to read uploaded image",
                "path_checked": temp_path
            }, status_code=400)

        # Save source image
        cv2.imwrite(source_path, img)
        
        # Process with YOLO using provided confidence threshold
        results = model(img, conf=min_conf)
        result = results[0]
        
        # Extract all detections without filtering by class
        all_detections = []
        overlay_img = img.copy()
        
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
                
                # Add ALL detections to the list
                all_detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
                
                # Draw ALL detections on overlay image
                if output_image == 1:
                    # Color mapping based on class
                    color_map = {
                        "person": (0, 255, 0),     # Green for person
                        "weapon": (0, 0, 255),     # Red for weapons
                        "suspicious": (0, 165, 255),  # Orange for suspicious
                        "helmet": (255, 0, 0),     # Blue for helmet
                        "mask": (255, 0, 0),       # Blue for mask
                        "default": (255, 255, 0)   # Yellow for unknown classes
                    }
                    
                    color = color_map.get(cls_name.lower(), color_map["default"])
                    
                    # Draw bounding box and label
                    cv2.rectangle(overlay_img, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(overlay_img, f"{cls_name} {conf:.2f}", 
                              (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Save overlay image if requested
        overlay_path = None
        if output_image == 1:
            overlay_name = f"all_overlay_{base_filename}"
            overlay_path = os.path.join(OUTPUT_DIR, overlay_name)
            cv2.imwrite(overlay_path, overlay_img)
            logger.debug(f"Saved ALL detections overlay image to {overlay_path}")
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Return comprehensive response
        response = {
            "status": "success",
            "camera_id": camera_id,
            "timestamp": datetime.now(india_tz).isoformat(),
            "all_detections": all_detections,
            "classes_in_model": model.names if hasattr(model, 'names') else {},
            "confidence_thresholds": CONFIDENCE_THRESHOLDS,
            "source_image": source_path,
            "min_confidence_used": min_conf,
            "total_detections": len(all_detections)
        }
        
        if overlay_path:
            response["overlay_image_path"] = overlay_path
            
        return response
    
    except Exception as e:
        logger.error(f"Error processing image for all detections: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Error processing image: {str(e)}"
        }, status_code=500)
