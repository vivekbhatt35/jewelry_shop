import os
import re
import time
from datetime import datetime
import glob
import logging
from utils.logger import setup_logger

# Set up logger
logger = setup_logger("Cleanup-Service")

class ImageCleaner:
    def __init__(self, image_dir="output_image", min_age_minutes=30):
        """Initialize the image cleaner.
        
        Args:
            image_dir (str): Directory containing images
            min_age_minutes (int): Minimum age of images in minutes before considering deletion
        """
        self.image_dir = image_dir
        self.min_age_minutes = min_age_minutes
        logger.info(f"Image cleaner initialized for {image_dir}, min age: {min_age_minutes} minutes")

    def is_older_than(self, file_path, minutes):
        """Check if a file is older than the specified number of minutes."""
        if not os.path.exists(file_path):
            return False
            
        file_time = os.path.getmtime(file_path)
        current_time = time.time()
        return (current_time - file_time) > (minutes * 60)

    def find_old_images(self):
        """Find source and overlay images older than min_age_minutes."""
        source_pattern = os.path.join(self.image_dir, "source_*")
        overlay_pattern = os.path.join(self.image_dir, "overlay_*")
        
        source_files = [f for f in glob.glob(source_pattern) if self.is_older_than(f, self.min_age_minutes)]
        overlay_files = [f for f in glob.glob(overlay_pattern) if self.is_older_than(f, self.min_age_minutes)]
        
        logger.info(f"Found {len(source_files)} source images and {len(overlay_files)} overlay images older than {self.min_age_minutes} minutes")
        return source_files, overlay_files

    def identify_unused_images(self, source_files, overlay_files, alert_images=None):
        """Identify old source and overlay images that should be cleaned up."""
        # Return all old files for deletion - we don't need to match with alerts
        # since the alert creation endpoint handles that logic
        to_delete = source_files + overlay_files
        logger.info(f"Found {len(to_delete)} old images to delete")
        
        logger.info(f"Found {len(to_delete)} images to delete (no alerts associated)")
        return to_delete

    def delete_files(self, files, dry_run=False):
        """Delete the specified files."""
        if not files:
            logger.info("No images to delete.")
            return 0
        
        count = 0
        for file in files:
            if dry_run:
                logger.info(f"Would delete: {file}")
            else:
                try:
                    os.remove(file)
                    logger.info(f"Deleted: {file}")
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting {file}: {e}")
        
        if not dry_run:
            logger.info(f"Deleted {count} unused images")
        return count

    def cleanup(self, dry_run=False):
        """Run the cleanup process."""
        logger.info(f"Starting image cleanup process, dry_run={dry_run}")
        
        # Find old images
        source_files, overlay_files = self.find_old_images()
        
        # Get all old files for deletion
        to_delete = self.identify_unused_images(source_files, overlay_files)
        
        # Delete files
        deleted_count = self.delete_files(to_delete, dry_run)
        
        logger.info(f"Cleanup complete. Source images: {len(source_files)}, "
                   f"Overlay images: {len(overlay_files)}, "
                   f"Images deleted: {deleted_count}")
        
        return deleted_count


def delete_unused_image_pair(source_path, output_dir="output_image"):
    """Delete a source image and its corresponding overlay image when no alert is generated.
    
    Args:
        source_path (str): Path to the source image
        output_dir (str): Directory containing output images
        
    Returns:
        tuple: (success, deleted_files) - success is True if deletion was successful,
               deleted_files is a list of deleted file paths
    """
    deleted_files = []
    try:
        # Check if the source path exists
        if not os.path.exists(source_path):
            logger.warning(f"Source image does not exist: {source_path}")
            return False, deleted_files
        
        # Delete source image
        source_base = os.path.basename(source_path)
        os.remove(source_path)
        deleted_files.append(source_path)
        logger.debug(f"Deleted source image: {source_path}")
        
        # Try to find and delete corresponding overlay image
        if source_base.startswith("source_"):
            # Extract parts from the source filename
            parts = source_base.split("_", 1)
            if len(parts) > 1:
                # Construct overlay filename
                overlay_base = "overlay_" + parts[1]
                overlay_path = os.path.join(output_dir, overlay_base)
                
                if os.path.exists(overlay_path):
                    os.remove(overlay_path)
                    deleted_files.append(overlay_path)
                    logger.debug(f"Deleted corresponding overlay image: {overlay_path}")
        
        return True, deleted_files
    except Exception as e:
        logger.error(f"Error deleting unused image pair: {str(e)}")
        logger.exception("Detailed image deletion exception:")
        return False, deleted_files


def run_cleanup(image_dir="output_image", min_age_minutes=30, dry_run=False):
    """Run the cleanup process with the specified parameters."""
    cleaner = ImageCleaner(image_dir, min_age_minutes)
    return cleaner.cleanup(dry_run)


# For testing directly
if __name__ == "__main__":
    cleaner = ImageCleaner()
    cleaner.cleanup(dry_run=True)  # Set to False to actually delete files
