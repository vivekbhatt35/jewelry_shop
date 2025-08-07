#!/bin/bash

echo "Temporarily disabling alert throttling for testing..."

# Create override file inside the container to disable throttling
docker exec -it yolo_pose_api-alert-logic-1 /bin/bash -c "echo 'GLOBAL_ALERT_COOLDOWN = 0' > /tmp/override.py"

# Tell Python to import this override file
docker exec -it yolo_pose_api-alert-logic-1 /bin/bash -c "echo 'import sys; sys.path.insert(0, \"/tmp\")' > /tmp/sitecustomize.py"
docker exec -it yolo_pose_api-alert-logic-1 /bin/bash -c "export PYTHONPATH=/tmp:\${PYTHONPATH}"

# Restart the alert-logic service
docker-compose restart alert-logic

echo "Alert throttling disabled. The service will now generate alerts without the throttling cooldown."
echo "Waiting for service to restart..."
sleep 5
echo "Done. Watch for new alerts in the logs."
