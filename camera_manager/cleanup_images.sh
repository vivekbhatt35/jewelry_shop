#!/bin/bash

# Script to clean up old output images based on age (default: 7 days)
# Usage: ./cleanup_images.sh [days]

DAYS=${1:-7}
OUTPUT_DIR="./output_image"

echo "Cleaning up images older than $DAYS days from $OUTPUT_DIR"

# Find and delete files older than specified days
find $OUTPUT_DIR -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.JPG" -mtime +$DAYS -delete
find $OUTPUT_DIR -type f -name "overlay_*.jpg" -o -name "overlay_*.jpeg" -o -name "overlay_*.png" -o -name "overlay_*.JPG" -mtime +$DAYS -delete
find $OUTPUT_DIR -type f -name "source_*.jpg" -o -name "source_*.jpeg" -o -name "source_*.png" -o -name "source_*.JPG" -mtime +$DAYS -delete
find $OUTPUT_DIR -type f -name "alertoverlay_*.jpg" -o -name "alertoverlay_*.jpeg" -o -name "alertoverlay_*.png" -o -name "alertoverlay_*.JPG" -mtime +$DAYS -delete

echo "Cleanup complete"
