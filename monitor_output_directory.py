#!/usr/bin/env python3
"""
Monitor script to observe file creation and deletion in the output directory.
"""

import os
import time
import argparse
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MonitorScript")

def monitor_directory(directory, interval=5, duration=300):
    """
    Monitor a directory for file changes.
    
    Args:
        directory (str): Directory to monitor
        interval (int): Check interval in seconds
        duration (int): Total monitoring duration in seconds
    """
    logger.info(f"Starting to monitor directory: {directory}")
    logger.info(f"Checking every {interval} seconds for {duration} seconds total")
    
    start_time = time.time()
    end_time = start_time + duration
    
    # Initial file count
    file_counts = {
        'source': 0,
        'overlay': 0,
        'alert': 0,
        'other': 0
    }
    
    previous_files = set()
    
    while time.time() < end_time:
        current_files = set(os.listdir(directory))
        
        # Classify files
        source_files = {f for f in current_files if f.startswith('source_')}
        overlay_files = {f for f in current_files if f.startswith('overlay_')}
        alert_files = {f for f in current_files if f.startswith('alert_')}
        other_files = current_files - source_files - overlay_files - alert_files
        
        # Update counts
        file_counts = {
            'source': len(source_files),
            'overlay': len(overlay_files),
            'alert': len(alert_files),
            'other': len(other_files)
        }
        
        # Detect changes
        new_files = current_files - previous_files
        deleted_files = previous_files - current_files
        
        # Report changes
        if new_files:
            logger.info(f"New files: {', '.join(new_files)}")
        
        if deleted_files:
            logger.info(f"Deleted files: {', '.join(deleted_files)}")
        
        # Report counts
        logger.info(f"Current file counts - Source: {file_counts['source']}, "
                   f"Overlay: {file_counts['overlay']}, Alert: {file_counts['alert']}, "
                   f"Other: {file_counts['other']}")
        
        # Update previous files
        previous_files = current_files
        
        # Wait for next check
        time.sleep(interval)
    
    logger.info(f"Monitoring completed after {duration} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor file changes in the output directory")
    parser.add_argument("--directory", default="output_image", help="Directory to monitor")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in seconds")
    parser.add_argument("--duration", type=int, default=300, help="Total monitoring duration in seconds")
    
    args = parser.parse_args()
    
    monitor_directory(args.directory, args.interval, args.duration)
