#!/bin/bash

# Fix the draw_detection_boxes function in detection_analysis.py
echo "Fixing draw_detection_boxes function in detection_analysis.py..."

# Create a fixed version of the function
cat << 'EOF' > fixed_draw_detection_boxes.py
def draw_detection_boxes(image, detections, indices=None, alert_types=None):
    """
    Draw bounding boxes on an image
    
    Args:
        image: OpenCV image
        detections: List of detection dictionaries
        indices: Optional list of detection indices that triggered alerts
        alert_types: Optional mapping from indices to alert types
    
    Returns:
        image: OpenCV image with bounding boxes drawn
    """
    img_copy = image.copy()
    
    # Convert the detections to a format we can work with
    bboxes = []
    
    for i, detection in enumerate(detections):
        class_name = detection.get("class_name", "unknown")
        confidence = detection.get("confidence", 0)
        bbox = detection.get("bbox", [0, 0, 10, 10])
        
        # Determine if this detection is an alert
        is_alert = indices is not None and i in indices
        
        # Get alert types for this detection if available
        detection_alert_types = []
        if is_alert and alert_types and i in alert_types:
            detection_alert_types = alert_types[i]
        
        bboxes.append({
            "bbox": bbox,
            "class_name": class_name,
            "confidence": confidence,
            "is_alert": is_alert,
            "alert_types": detection_alert_types
        })
    
    # Draw the boxes
    for bbox_dict in bboxes:
        bbox = bbox_dict.get("bbox", [0, 0, 10, 10])
        class_name = bbox_dict.get("class_name", "unknown")
        confidence = bbox_dict.get("confidence", 0)
        is_alert = bbox_dict.get("is_alert", False)
        alert_types_list = bbox_dict.get("alert_types", [])
        
        x, y, w, h = bbox
        
        # Choose color: red for alerts, green otherwise
        if is_alert:
            color = (0, 0, 255)  # BGR: Red for alerts
        else:
            color = (0, 255, 0)  # BGR: Green for non-alerts
        
        # Draw the bounding box
        cv2.rectangle(img_copy, (int(x), int(y)), (int(x + w), int(y + h)), color, 2)
        
        # Draw the label
        if is_alert and alert_types_list:
            label = f"{class_name}: {confidence:.2f} ({', '.join(alert_types_list)})"
        else:
            label = f"{class_name}: {confidence:.2f}"
            
        cv2.putText(img_copy, label, (int(x), int(y - 10)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    return img_copy
EOF

# Start the container if it's not running
CONTAINER_ID=$(docker ps -q -f name=yolo_pose_api-alert-logic)
if [ -z "$CONTAINER_ID" ]; then
    echo "Starting alert-logic container..."
    docker-compose up -d alert-logic
    sleep 5
    CONTAINER_ID=$(docker ps -q -f name=yolo_pose_api-alert-logic)
fi

# Copy the fixed function into the container
echo "Copying fixed draw_detection_boxes function to container..."
docker cp fixed_draw_detection_boxes.py "$CONTAINER_ID:/app/fixed_draw_detection_boxes.py"

# Replace the function in detection_analysis.py
echo "Replacing draw_detection_boxes function in detection_analysis.py..."
docker exec "$CONTAINER_ID" bash -c "cat /app/fixed_draw_detection_boxes.py > /tmp/temp_func && \
    sed -i '/def draw_detection_boxes/,/return img_copy/c\\' /app/alert_logic/logic/detection_analysis.py && \
    cat /tmp/temp_func >> /app/alert_logic/logic/detection_analysis.py"

# Restart the container
echo "Restarting alert-logic service..."
docker-compose restart alert-logic

echo "Done! Fixed the draw_detection_boxes function."
echo "Check the logs to verify the fix:"
echo "docker-compose logs -f alert-logic"
