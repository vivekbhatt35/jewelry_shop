#!/bin/bash

# Final fix for alert logic - correct the draw_detection_boxes function call
echo "Creating fixed app.py to correct draw_detection_boxes call..."

# Create a temporary patch file
cat << 'EOF' > app_patch.py
                    # Draw bounding boxes for alerted objects
                    detection_bboxes = get_detection_bboxes(detections_list)
                    base_img = draw_detection_boxes(base_img, detection_bboxes)
EOF

# Apply the patch using sed
docker exec yolo_pose_api-alert-logic-1 bash -c "sed -i '267,267s/.*base_img = draw_detection_boxes.*/                    base_img = draw_detection_boxes(base_img, detection_bboxes)/' /app/alert_logic/app.py"

# Restart the alert-logic service
echo "Restarting alert-logic service..."
docker-compose restart alert-logic

echo "Checking logs after fix..."
sleep 2
docker-compose logs --tail=20 alert-logic

echo ""
echo "Fix has been applied! The system should now correctly handle mask, helmet, and suspicious alerts."
echo "You can monitor the logs with: docker-compose logs -f alert-logic"
