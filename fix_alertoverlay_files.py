#!/usr/bin/env python3
import os
import glob
import re
from datetime import datetime
import pytz
import shutil
import sys

# Create a timezone object for India
india_tz = pytz.timezone('Asia/Kolkata')

def fix_alertoverlay_files(output_dir='/app/output_image', camera_id="CAM_001"):
    """
    Find and rename alertoverlay_UUID.jpg files to our standardized format
    
    Args:
        output_dir: Directory containing images
        camera_id: Camera ID to use in the new filename
    """
    print(f"Looking for alertoverlay files in {output_dir}...")
    
    # Find all alertoverlay files
    alertoverlay_pattern = os.path.join(output_dir, "alertoverlay_*.jpg")
    alertoverlay_files = glob.glob(alertoverlay_pattern)
    
    if not alertoverlay_files:
        print("No alertoverlay files found.")
        return 0
    
    print(f"Found {len(alertoverlay_files)} alertoverlay files.")
    
    # Create timestamp with current time
    timestamp = datetime.now(india_tz).strftime("%H%M%S")
    
    # Process each file
    renamed_count = 0
    for old_path in alertoverlay_files:
        try:
            filename = os.path.basename(old_path)
            
            # Extract UUID from filename if possible
            uuid_match = re.search(r'alertoverlay_([a-f0-9\-]+)', filename)
            uuid_part = uuid_match.group(1) if uuid_match else 'unknown'
            
            # Create new standardized filename
            new_filename = f"alert_{camera_id}_{timestamp}_{renamed_count}_Fixed.jpg"
            new_path = os.path.join(output_dir, new_filename)
            
            print(f"Renaming {filename} -> {new_filename}")
            
            # Copy first, then remove to ensure we don't lose data
            shutil.copy2(old_path, new_path)
            if os.path.exists(new_path) and os.path.getsize(new_path) > 0:
                os.remove(old_path)
                renamed_count += 1
            else:
                print(f"WARNING: Failed to properly copy {filename}")
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    print(f"Successfully renamed {renamed_count} files.")
    return renamed_count

if __name__ == "__main__":
    # Handle command line arguments
    output_dir = '/app/output_image'
    camera_id = "CAM_001"
    
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    
    if len(sys.argv) > 2:
        camera_id = sys.argv[2]
    
    fix_alertoverlay_files(output_dir, camera_id)
