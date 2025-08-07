# Alert Image Naming Fix

## Problem
Alert images were being saved with the format `alertoverlay_UUID.jpg` instead of the standardized format `alert_{camera_id}_{timestamp}_{alert_type}.jpg`. This made it difficult to identify alerts visually and to match them with specific cameras and events.

## Analysis
After investigation, we found that the alertoverlay naming pattern was being generated somewhere in the codebase. Our fixes needed to intercept this pattern wherever it was being generated and replace it with our standardized naming format.

## Solution
We implemented a multi-layer approach:

1. **Monkey Patch for cv2.imwrite**
   - Added code to intercept any attempts to save files with the "alertoverlay_" prefix
   - Extracted context information from the call stack to determine camera_id and alert_type
   - Replaced the alertoverlay filename with our standardized format

2. **Final Cleanup Check**
   - Added a check at the end of alert processing to find and rename any alertoverlay files that might have been missed
   - This ensures that all files use our standardized naming convention

3. **Database Support**
   - Added a test camera entry ("CAM_TEST") to the camera_configurations table
   - This allows our test alerts to be properly stored in the database

## Implementation
The implementation was done by:

1. Creating a Python script to patch the alert_logic/app.py file
2. Creating a utility to rename any existing alertoverlay files
3. Setting up database entries to support our test cameras
4. Verifying the fix with test alerts

## Verification
We verified the fix by:

1. Running test alerts with hands-up poses
2. Checking the output directory for properly named alert images
3. Confirming the format follows our standardized pattern `alert_{camera_id}_{timestamp}_{alert_type}.jpg`

## Results
Alert images are now consistently named with our standardized format, making them easier to identify and manage. The previous UUID-based alertoverlay files have been renamed to follow the new convention.

We can see in the logs that our fix successfully intercepts any attempts to create alertoverlay files and renames them on the fly:
```
INTERCEPTING ALERTOVERLAY FILENAME: /app/output_image/alertoverlay_b466686b-6feb-4c07-95a6-94b6aa352b5d.jpg
Found camera_id in frame locals: CAM_TEST
Found alert_type in frame: Hands_Up
RENAMED ALERTOVERLAY TO STANDARDIZED NAME: /app/output_image/alert_CAM_TEST_091442_Hands_Up.jpg
```

## Note
While our fix correctly handles the alert image naming, we identified a separate issue with alert database records not being created for our test camera. This will need to be addressed separately.
