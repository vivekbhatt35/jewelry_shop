import os
import logging
from datetime import datetime
import pathlib
import pytz
import sys

def setup_logger(service_name):
    """
    Set up a logger with specific formatting and file structure.
    Creates logs in YYYY/MM/DD folder structure using India timezone.
    
    Args:
        service_name: Name of the service for identification in logs
        
    Returns:
        logger: Configured logger instance
    """
    # Use India timezone (IST)
    india_tz = pytz.timezone('Asia/Kolkata')
    today = datetime.now(india_tz)
    
    # Create year/month/day directory structure
    log_dir = os.path.join(
        os.environ.get('LOG_DIR', 'logs'),
        str(today.year),
        str(today.month),
        str(today.day)
    )
    
    # Ensure log directory exists
    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Create service-specific log file
    service_log_file = os.path.join(log_dir, f"{service_name.lower().replace(' ', '_')}.log")
    combined_log_file = os.path.join(log_dir, "combined.log")
    debug_file = os.path.join(log_dir, f"{service_name.lower().replace(' ', '_')}_debug.log")
    
    # Create logger
    logger = logging.getLogger(service_name)
    # Set to DEBUG level to capture detailed information
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create IST timezone formatter with converter function
    def india_time_converter(*args):
        return datetime.now(india_tz).timetuple()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(name)s] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    formatter.converter = india_time_converter
    
    # Create service-specific file handler (INFO level)
    service_handler = logging.FileHandler(service_log_file)
    service_handler.setLevel(logging.INFO)
    service_handler.setFormatter(formatter)
    logger.addHandler(service_handler)
    
    # Create combined log file handler (INFO level)
    combined_handler = logging.FileHandler(combined_log_file)
    combined_handler.setLevel(logging.INFO)
    combined_handler.setFormatter(formatter)
    logger.addHandler(combined_handler)
    
    # Create debug log file handler (DEBUG level)
    debug_handler = logging.FileHandler(debug_file)
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    logger.addHandler(debug_handler)
    
    # Add console handler (INFO level for normal use, DEBUG for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG for better insight
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
