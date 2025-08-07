#!/bin/bash

# Run the fix_alertoverlay_files.py script inside the container
echo "Running fix_alertoverlay_files.py inside alert-logic container..."
docker-compose exec -T alert-logic python3 /app/fix_alertoverlay_files.py /app/output_image CAM_TEST

# Check if we still have any alertoverlay files
echo "Checking for remaining alertoverlay files..."
docker-compose exec -T alert-logic bash -c "ls -la /app/output_image/alertoverlay_* 2>/dev/null || echo 'No alertoverlay files found'"

# List all alert files
echo "Checking for alert files with our standardized naming..."
docker-compose exec -T alert-logic bash -c "ls -la /app/output_image/alert_* 2>/dev/null || echo 'No alert files found'"

echo "Done!"
