from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from logic.pose_analysis import hands_up_detect, get_person_bboxes, draw_bboxes
from datetime import datetime
import cv2
import os
import json
import uuid

app = FastAPI()
OUTPUT_DIR = "output_image"
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
        poses_list = json.loads(poses)
    except Exception:
        return JSONResponse(content={"error": "Invalid poses data"}, status_code=400)

    # Load the image to draw overlays
    base_img = cv2.imread(image_source)
    if base_img is None:
        return JSONResponse(content={"error": "Image could not be loaded"}, status_code=400)

    # Analyze for hands up
    person_alert_indices = hands_up_detect(poses_list)
    result_alerts = ["Hands_Up"] if person_alert_indices else []

    # Draw bounding boxes for alerted persons
    image_bb = []
    if person_alert_indices:
        person_bboxes = get_person_bboxes(poses_list)
        base_img = draw_bboxes(base_img, person_bboxes, person_alert_indices, color=(0, 0, 255))
        image_bb = [person_bboxes[idx] for idx in person_alert_indices]

    # Save new overlay if we have alerts
    saved_overlay_path = None
    if result_alerts:
        unique_id = str(uuid.uuid4())
        file_name = f"alertoverlay_{unique_id}.jpg"
        saved_overlay_path = os.path.join(OUTPUT_DIR, file_name)
        cv2.imwrite(saved_overlay_path, base_img)

    return JSONResponse(content={
        "type_of_alert": ",".join(result_alerts) if result_alerts else "No_Alert",
        "SourceID": camera_id,
        "Detection_type": detection_type,
        "date_Time": date_time,
        "Image_source": image_source,
        "Image_overlay": saved_overlay_path,
        "Image_bb": image_bb if image_bb else None
    })
