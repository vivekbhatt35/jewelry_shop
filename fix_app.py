#!/usr/bin/env python3
# fix_app.py - Apply our permanent fix to alert_logic/app.py

import sys
import re

def main():
    """Main function to apply the fix to app.py"""
    if len(sys.argv) < 2:
        print("Usage: python fix_app.py /path/to/app.py")
        sys.exit(1)
        
    app_path = sys.argv[1]
    print(f"Fixing {app_path}...")
    
    # Read the current file
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Apply our first fix - intercept any cv2.imwrite calls that would create alertoverlay files
    monkey_patch_code = """
# Monkey patch cv2.imwrite to prevent alertoverlay files
original_imwrite = cv2.imwrite
def patched_imwrite(filename, img):
    # Check for UUID-based alertoverlay pattern
    if 'alertoverlay_' in filename:
        logger.warning(f"INTERCEPTING ALERTOVERLAY FILENAME: {filename}")
        
        # Try to create a proper alert name instead
        try:
            # Extract camera_id from somewhere in the context
            camera_id = "UNKNOWN"
            # Look through stack frames to find camera_id in locals or function args
            import inspect
            frame = inspect.currentframe().f_back  # Get calling frame
            if 'camera_id' in frame.f_locals:
                camera_id = frame.f_locals['camera_id']
                logger.warning(f"Found camera_id in frame locals: {camera_id}")
            
            # Create standardized name
            timestamp = datetime.now(india_tz).strftime("%H%M%S")
            alert_type_str = "Alert"  # Default
            
            # Look for alert type in frame locals
            if 'result_alerts' in frame.f_locals and frame.f_locals['result_alerts']:
                alert_type_str = '_'.join(frame.f_locals['result_alerts'])
                logger.warning(f"Found alert_type in frame: {alert_type_str}")
            
            new_filename = os.path.join(OUTPUT_DIR, f"alert_{camera_id}_{timestamp}_{alert_type_str}.jpg")
            logger.warning(f"RENAMED ALERTOVERLAY TO STANDARDIZED NAME: {new_filename}")
            return original_imwrite(new_filename, img)
        except Exception as e:
            logger.error(f"Error trying to rename alertoverlay file: {str(e)}")
            # Create a fallback standardized name
            timestamp = datetime.now(india_tz).strftime("%H%M%S")
            new_filename = os.path.join(OUTPUT_DIR, f"alert_UNKNOWN_{timestamp}_Alert.jpg")
            logger.warning(f"Using fallback standardized name: {new_filename}")
            return original_imwrite(new_filename, img)
    
    return original_imwrite(filename, img)
cv2.imwrite = patched_imwrite
"""
    
    # Find the right spot to insert our monkey patch
    import_pattern = r'from utils\.logger import setup_logger.*?\n'
    if re.search(import_pattern, content):
        content = re.sub(import_pattern, 
                        r'from utils.logger import setup_logger\n\n# --------------- ALERT IMAGE NAMING FIX ---------------\n' + monkey_patch_code + '\n# --------------- END OF FIX ---------------\n\n', 
                        content)
    
    # Our second fix - add a cleanup at the end
    cleanup_code = """
        # Final check for alertoverlay files - rename any that still exist
        alertoverlay_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('alertoverlay_')]
        if alertoverlay_files:
            logger.warning(f"Found {len(alertoverlay_files)} alertoverlay files at end of processing - renaming them")
            for alertoverlay_file in alertoverlay_files:
                try:
                    old_path = os.path.join(OUTPUT_DIR, alertoverlay_file)
                    
                    # Create a standardized name
                    timestamp = datetime.now(india_tz).strftime("%H%M%S")
                    new_filename = f"alert_{camera_id}_{timestamp}_Fixed.jpg"
                    new_path = os.path.join(OUTPUT_DIR, new_filename)
                    
                    # Rename the file
                    os.rename(old_path, new_path)
                    logger.warning(f"Renamed {alertoverlay_file} to {new_filename}")
                except Exception as e:
                    logger.error(f"Error renaming {alertoverlay_file}: {str(e)}")
"""
    
    # Find where to insert our cleanup code
    end_pattern = r'logger\.info\(f"Alert processing completed for camera {camera_id}"\)\s+return JSONResponse\(content=response_data\)'
    if re.search(end_pattern, content):
        content = re.sub(end_pattern, 
                       cleanup_code + '\n        logger.info(f"Alert processing completed for camera {camera_id}")\n        return JSONResponse(content=response_data)',
                       content)
    
    # Write the fixed file
    with open(app_path, 'w') as f:
        f.write(content)
    
    print(f"Successfully applied fixes to {app_path}")

if __name__ == "__main__":
    main()
