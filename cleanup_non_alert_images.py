#!/usr/bin/env python3
"""
Manual cleanup script to remove non-alert images from the output directory.
This script will delete all source and overlay images that don't have corresponding alert images.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CleanupScript")

def clean_output_directory(output_dir, dry_run=True, min_age_minutes=0):
    """
    Clean the output directory by removing all source and overlay images
    that don't have corresponding alert images.
    
    Args:
        output_dir (str): Path to the output directory
        dry_run (bool): If True, just print what would be deleted without actually deleting
        min_age_minutes (int): Only delete files older than this many minutes
        
    Returns:
        int: Number of files deleted
    """
    logger.info(f"Cleaning output directory: {output_dir}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Min age: {min_age_minutes} minutes")
    
    if not os.path.isdir(output_dir):
        logger.error(f"Output directory does not exist: {output_dir}")
        return 0
    
    # Get all files in the directory
    all_files = os.listdir(output_dir)
    
    # Group files by type
    source_files = [f for f in all_files if f.startswith("source_")]
    overlay_files = [f for f in all_files if f.startswith("overlay_")]
    alert_files = [f for f in all_files if f.startswith("alert_")]
    
    logger.info(f"Found {len(source_files)} source files, {len(overlay_files)} overlay files, and {len(alert_files)} alert files")
    
    # Extract camera IDs and timestamps from alert files
    alert_identifiers = set()
    for alert_file in alert_files:
        parts = alert_file.split("_")
        if len(parts) >= 3:
            # Extract camera ID and timestamp from alert_CAMID_TIMESTAMP_TYPE.ext
            camera_id = parts[1]
            timestamp = parts[2]
            alert_identifiers.add(f"{camera_id}_{timestamp}")
    
    logger.info(f"Found {len(alert_identifiers)} unique alert identifiers")
    
    # Find source and overlay files that don't have corresponding alerts
    files_to_delete = []
    
    current_time = datetime.now().timestamp()
    min_age_seconds = min_age_minutes * 60
    
    for file_type, files in [("source", source_files), ("overlay", overlay_files)]:
        for file in files:
            file_path = os.path.join(output_dir, file)
            
            # Skip files that aren't old enough
            if min_age_minutes > 0:
                file_age_seconds = current_time - os.path.getmtime(file_path)
                if file_age_seconds < min_age_seconds:
                    logger.debug(f"Skipping {file}: too recent ({file_age_seconds/60:.1f} minutes old)")
                    continue
            
            # Extract identifier (camera ID and timestamp)
            parts = file.split("_")
            if len(parts) >= 3:
                identifier = f"{parts[1]}_{parts[2]}"
                
                # If this identifier isn't in the alerts, delete the file
                if identifier not in alert_identifiers:
                    files_to_delete.append(file_path)
    
    logger.info(f"Found {len(files_to_delete)} files to delete")
    
    # Delete files
    deleted_count = 0
    for file_path in files_to_delete:
        try:
            if dry_run:
                logger.info(f"Would delete: {file_path}")
            else:
                os.remove(file_path)
                logger.info(f"Deleted: {file_path}")
                deleted_count += 1
        except Exception as e:
            logger.error(f"Error deleting {file_path}: {e}")
    
    if dry_run:
        logger.info(f"Dry run completed. Would have deleted {len(files_to_delete)} files.")
    else:
        logger.info(f"Cleanup completed. Deleted {deleted_count} files.")
    
    return deleted_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up non-alert images from the output directory")
    parser.add_argument("--output-dir", default="output_image", help="Path to the output directory")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually delete files, just print what would be deleted")
    parser.add_argument("--min-age", type=int, default=10, help="Only delete files older than this many minutes")
    
    args = parser.parse_args()
    
    clean_output_directory(args.output_dir, args.dry_run, args.min_age)
