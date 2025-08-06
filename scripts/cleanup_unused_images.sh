#!/bin/bash

# =========================================================
#  CLEANUP UNUSED IMAGES - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  CLEANING UP UNUSED IMAGES"
echo "==========================================================="

# Directory containing images
IMAGE_DIR="output_image"
# How old the images should be (in minutes) before we consider deleting them
MIN_AGE_MINUTES=30
# Dry run (set to true to just show what would be deleted)
DRY_RUN=true

# Get list of alert image timestamps with their camera IDs
echo "Step 1: Finding alert images..."
TEMP_ALERT_KEYS=$(mktemp)

for alert_file in "$IMAGE_DIR"/alert_*; do
    if [ -f "$alert_file" ]; then
        # Extract datetime from alert filename
        filename=$(basename "$alert_file")
        # Extract camera_id and time using sed
        camera_id=$(echo "$filename" | sed -E 's/alert_([A-Za-z0-9_]+)_([0-9]{6})_.*/\1/')
        time=$(echo "$filename" | sed -E 's/alert_([A-Za-z0-9_]+)_([0-9]{6})_.*/\2/')
        
        # Use just the time (HHMMSS) as key since that's what we have in the new format
        key="${camera_id}_${time}"
        echo "$key" >> "$TEMP_ALERT_KEYS"
        echo "  Alert found: $filename (key: $key)"
    fi
done

# Count alert images
alert_count=$(wc -l < "$TEMP_ALERT_KEYS")
echo "  Found $alert_count alert images"

# Get list of source and overlay images
echo ""
echo "Step 2: Finding source and overlay images older than $MIN_AGE_MINUTES minutes..."
SOURCE_FILES=$(find "$IMAGE_DIR" -type f -name "source_*" -mmin "+$MIN_AGE_MINUTES")
OVERLAY_FILES=$(find "$IMAGE_DIR" -type f -name "overlay_*" -mmin "+$MIN_AGE_MINUTES")

# Count of files to be processed
SOURCE_COUNT=$(echo "$SOURCE_FILES" | grep -c "^" || echo 0)
OVERLAY_COUNT=$(echo "$OVERLAY_FILES" | grep -c "^" || echo 0)

echo "  Found $SOURCE_COUNT source images and $OVERLAY_COUNT overlay images older than $MIN_AGE_MINUTES minutes"

# Files to delete
TO_DELETE_LIST=$(mktemp)

# Process source files
echo ""
echo "Step 3: Identifying images without corresponding alerts..."
for file in $SOURCE_FILES; do
    filename=$(basename "$file")
    # Extract datetime and camera parts
    date_part=$(echo "$filename" | sed -E 's/source_([0-9]{8})_([0-9]{6})_([A-Za-z0-9_]+)\..*/\1/')
    time_part=$(echo "$filename" | sed -E 's/source_([0-9]{8})_([0-9]{6})_([A-Za-z0-9_]+)\..*/\2/')
    camera_part=$(echo "$filename" | sed -E 's/source_([0-9]{8})_([0-9]{6})_([A-Za-z0-9_]+)\..*/\3/')
    
    # Create key using only camera_id and time (HHMMSS) to match alert format
    key="${camera_part}_${time_part}"
    
    # Check if there's a corresponding alert
    if ! grep -q "$key" "$TEMP_ALERT_KEYS"; then
        echo "$file" >> "$TO_DELETE_LIST"
    fi
done

# Process overlay files
for file in $OVERLAY_FILES; do
    filename=$(basename "$file")
    # Extract datetime and camera parts
    date_part=$(echo "$filename" | sed -E 's/overlay_([0-9]{8})_([0-9]{6})_([A-Za-z0-9_]+)\..*/\1/')
    time_part=$(echo "$filename" | sed -E 's/overlay_([0-9]{8})_([0-9]{6})_([A-Za-z0-9_]+)\..*/\2/')
    camera_part=$(echo "$filename" | sed -E 's/overlay_([0-9]{8})_([0-9]{6})_([A-Za-z0-9_]+)\..*/\3/')
    
    # Create key using only camera_id and time (HHMMSS) to match alert format
    key="${camera_part}_${time_part}"
    
    # Check if there's a corresponding alert
    if ! grep -q "$key" "$TEMP_ALERT_KEYS"; then
        echo "$file" >> "$TO_DELETE_LIST"
    fi
done

# Count of files to be deleted
DELETE_COUNT=$(wc -l < "$TO_DELETE_LIST")
echo "  Found $DELETE_COUNT images to delete (no alerts associated)"

# Delete files or show what would be deleted
echo ""
echo "Step 4: Removing unused images..."

if [ "$DELETE_COUNT" -eq 0 ]; then
    echo "  No images to delete."
else
    if [ "$DRY_RUN" = true ]; then
        echo "  DRY RUN - The following files would be deleted:"
        cat "$TO_DELETE_LIST" | while read file; do
            echo "  Would delete: $file"
        done
    else
        cat "$TO_DELETE_LIST" | while read file; do
            echo "  Deleting: $file"
            rm "$file"
        done
        echo "  Deleted $DELETE_COUNT unused images"
    fi
fi

# Clean up temp files
rm -f "$TEMP_ALERT_KEYS" "$TO_DELETE_LIST"

echo ""
echo "==========================================================="
echo "  CLEANUP COMPLETE"
echo "==========================================================="
echo ""
echo "Summary:"
echo "- Alert images found: $alert_count"
echo "- Source images older than $MIN_AGE_MINUTES minutes: $SOURCE_COUNT"
echo "- Overlay images older than $MIN_AGE_MINUTES minutes: $OVERLAY_COUNT"
echo "- Images without alerts deleted: $DELETE_COUNT"
echo ""
echo "To modify settings, edit the script variables:"
echo "- MIN_AGE_MINUTES: Only process images older than this many minutes"
echo "- DRY_RUN: Set to 'true' to preview deletions without actually deleting"
echo "==========================================================="
