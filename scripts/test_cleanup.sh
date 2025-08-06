#!/bin/bash

# =========================================================
#  TEST IMAGE CLEANUP - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  TESTING IMAGE CLEANUP"
echo "==========================================================="

# Default settings
MIN_AGE_MINUTES=0  # Set to 0 for testing so it includes all images
DRY_RUN=true       # Default to dry run for safety

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --age)
            MIN_AGE_MINUTES="$2"
            shift
            ;;
        --execute)
            DRY_RUN=false
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 [--age MINUTES] [--execute]"
            echo "  --age MINUTES: Only consider images older than MINUTES (default: 0)"
            echo "  --execute: Actually delete files (default: dry run only)"
            exit 1
            ;;
    esac
    shift
done

echo "Settings:"
echo "- Minimum age: ${MIN_AGE_MINUTES} minutes"
echo "- Mode: $([ "$DRY_RUN" = true ] && echo "DRY RUN (no files will be deleted)" || echo "EXECUTE (files will be deleted)")"

echo ""
echo "Step 1: Checking for alert images..."
ALERT_COUNT=$(find output_image -type f -name "alert_*" | wc -l)
echo "  Found ${ALERT_COUNT} alert images"

echo ""
echo "Step 2: Checking for source and overlay images..."
SOURCE_COUNT=$(find output_image -type f -name "source_*" -mmin +${MIN_AGE_MINUTES} | wc -l)
OVERLAY_COUNT=$(find output_image -type f -name "overlay_*" -mmin +${MIN_AGE_MINUTES} | wc -l)
echo "  Found ${SOURCE_COUNT} source images older than ${MIN_AGE_MINUTES} minutes"
echo "  Found ${OVERLAY_COUNT} overlay images older than ${MIN_AGE_MINUTES} minutes"

echo ""
echo "Step 3: Running cleanup script..."
if [ "$DRY_RUN" = true ]; then
    # Call the cleanup script in dry-run mode
    scripts/cleanup_unused_images.sh
else
    # Remove the DRY_RUN=true line and run the script
    sed -i.bak 's/DRY_RUN=true/DRY_RUN=false/' scripts/cleanup_unused_images.sh
    scripts/cleanup_unused_images.sh
    # Restore the original script
    mv scripts/cleanup_unused_images.sh.bak scripts/cleanup_unused_images.sh
fi

echo ""
echo "Step 4: Calling API endpoint (manual cleanup)..."
if [ "$DRY_RUN" = true ]; then
    curl -X POST "http://localhost:8012/cleanup?min_age_minutes=${MIN_AGE_MINUTES}&dry_run=true" \
        -H "Content-Type: application/json" | json_pp
else
    curl -X POST "http://localhost:8012/cleanup?min_age_minutes=${MIN_AGE_MINUTES}&dry_run=false" \
        -H "Content-Type: application/json" | json_pp
fi

echo ""
echo "==========================================================="
echo "  CLEANUP TEST COMPLETE"
echo "==========================================================="
echo ""
echo "NOTE: If you want to actually delete files, run:"
echo "  ./scripts/test_cleanup.sh --execute"
echo ""
echo "To set a minimum age (in minutes):"
echo "  ./scripts/test_cleanup.sh --age 30"
echo "==========================================================="
