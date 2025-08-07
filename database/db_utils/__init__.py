import os
import psycopg2
from psycopg2.extras import RealDictCursor
from utils.logger import setup_logger

logger = setup_logger("Database")

def get_db_connection():
    """
    Create a connection to the PostgreSQL database
    """
    try:
        # Get database connection string from environment variable
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/camera_system")
        
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        logger.debug("Database connection established")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

class CameraConfigRepository:
    """
    Repository for managing camera configurations in the database
    """
    def __init__(self):
        self.logger = setup_logger("CameraConfigRepo")
    
    def get_all_cameras(self):
        """
        Get all camera configurations from the database
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM camera_configurations")
                    return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Error fetching camera configurations: {str(e)}")
            return []
    
    def get_camera_by_id(self, camera_id):
        """
        Get a camera configuration by ID
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM camera_configurations WHERE camera_id = %s", (camera_id,))
                    return cur.fetchone()
        except Exception as e:
            self.logger.error(f"Error fetching camera {camera_id}: {str(e)}")
            return None
    
    def create_camera(self, camera_config):
        """
        Create a new camera configuration
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO camera_configurations 
                        (camera_id, camera_name, camera_url, camera_type, 
                         frame_interval, detection_enabled, pose_enabled, notify_enabled, 
                         resolution, username, password)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        camera_config.get('camera_id'),
                        camera_config.get('camera_name'),
                        camera_config.get('camera_url'),
                        camera_config.get('camera_type'),
                        camera_config.get('frame_interval', 1000),
                        camera_config.get('detection_enabled', True),
                        camera_config.get('pose_enabled', True),
                        camera_config.get('notify_enabled', True),
                        camera_config.get('resolution', '1280x720'),
                        camera_config.get('username'),
                        camera_config.get('password')
                    ))
                    return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error creating camera configuration: {str(e)}")
            raise
    
    def update_camera(self, camera_id, camera_config):
        """
        Update an existing camera configuration
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE camera_configurations SET
                        camera_name = %s,
                        camera_url = %s,
                        camera_type = %s,
                        frame_interval = %s,
                        detection_enabled = %s,
                        pose_enabled = %s,
                        notify_enabled = %s,
                        resolution = %s,
                        username = %s,
                        password = %s
                        WHERE camera_id = %s
                    """, (
                        camera_config.get('camera_name'),
                        camera_config.get('camera_url'),
                        camera_config.get('camera_type'),
                        camera_config.get('frame_interval', 1000),
                        camera_config.get('detection_enabled', True),
                        camera_config.get('pose_enabled', True),
                        camera_config.get('notify_enabled', True),
                        camera_config.get('resolution', '1280x720'),
                        camera_config.get('username'),
                        camera_config.get('password'),
                        camera_id
                    ))
                    return cur.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating camera {camera_id}: {str(e)}")
            raise
    
    def delete_camera(self, camera_id):
        """
        Delete a camera configuration
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM camera_configurations WHERE camera_id = %s", (camera_id,))
                    return cur.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting camera {camera_id}: {str(e)}")
            raise
    
    def generate_config_files(self, output_dir):
        """
        Generate configuration files for all cameras in the database
        """
        cameras = self.get_all_cameras()
        generated_files = []
        
        for camera in cameras:
            try:
                config_file = os.path.join(output_dir, f"{camera['camera_id']}.cfg")
                
                with open(config_file, 'w') as f:
                    # Camera section
                    f.write("[camera]\n")
                    f.write(f"camera_id = {camera['camera_id']}\n")
                    f.write(f"extract_interval = {camera['frame_interval'] // 1000}\n")
                    
                    # Determine if it's RTSP or file source
                    if camera['camera_type'] == 'rtsp':
                        f.write(f"rtsp_url = {camera['camera_url']}\n")
                        f.write("video_path = \n")
                        f.write("source_type = rtsp\n")
                    else:
                        f.write("rtsp_url = \n")
                        f.write(f"video_path = {camera['camera_url']}\n")
                        f.write("source_type = file\n")
                    
                    f.write("loop_video = false\n")
                    f.write("image_path = /app/output_image\n\n")
                    
                    # Analytics section
                    f.write("[analytics]\n")
                    f.write(f"enabled = {str(camera['detection_enabled']).lower()}\n")
                    f.write(f"pose_detection = {str(camera['pose_enabled']).lower()}\n")
                    f.write(f"object_detection = {str(camera['detection_enabled']).lower()}\n\n")
                    
                    # Tracking section - use default values
                    f.write("[tracking]\n")
                    f.write("enabled = true\n")
                    f.write("max_distance_threshold = 200\n")
                    f.write("min_iou_threshold = 0.1\n")
                    f.write("use_spatial = true\n")
                    f.write("use_appearance = true\n\n")
                    
                    # Alerts section - use default values
                    f.write("[alerts]\n")
                    f.write("alert_interval = 1200\n")
                    f.write("track_unique_people = true\n")
                    f.write("person_memory = 3600\n")
                
                generated_files.append(config_file)
                self.logger.info(f"Generated config file for camera {camera['camera_id']}")
                
            except Exception as e:
                self.logger.error(f"Error generating config for camera {camera['camera_id']}: {str(e)}")
        
        return generated_files

class AlertRepository:
    """
    Repository for managing alerts in the database
    """
    def __init__(self):
        self.logger = setup_logger("AlertRepo")
    
    def create_alert(self, alert_data):
        """
        Create a new alert in the database
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get alert type ID
                    cur.execute("SELECT id FROM alert_types WHERE name = %s", (alert_data.get('alert_type'),))
                    alert_type_result = cur.fetchone()
                    
                    # If alert type doesn't exist, create it
                    if not alert_type_result:
                        self.logger.info(f"Creating new alert type: {alert_data.get('alert_type')}")
                        cur.execute(
                            "INSERT INTO alert_types (name, description) VALUES (%s, %s) RETURNING id", 
                            (alert_data.get('alert_type'), f"Auto-created alert type: {alert_data.get('alert_type')}")
                        )
                        alert_type_id = cur.fetchone()[0]
                    else:
                        alert_type_id = alert_type_result[0]
                    
                    cur.execute("""
                        INSERT INTO alerts 
                        (camera_id, alert_type_id, alert_datetime, source_image_path, 
                         overlay_image_path, alert_image_path, persons_count, alert_details)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        RETURNING id
                    """, (
                        alert_data.get('camera_id'),
                        alert_type_id,
                        alert_data.get('datetime'),
                        alert_data.get('source_image_path'),
                        alert_data.get('overlay_image_path'),
                        alert_data.get('alert_image_path'),
                        alert_data.get('persons_count', 0),
                        alert_data.get('details', '{}')
                    ))
                    return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error creating alert: {str(e)}")
            raise
    
    def get_alerts(self, limit=100, offset=0, camera_id=None, start_date=None, end_date=None, alert_type=None):
        """
        Get alerts with filtering options
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT a.*, at.name as alert_type_name
                        FROM alerts a
                        LEFT JOIN alert_types at ON a.alert_type_id = at.id
                        WHERE 1=1
                    """
                    params = []
                    
                    if camera_id:
                        query += " AND a.camera_id = %s"
                        params.append(camera_id)
                    
                    if start_date:
                        query += " AND a.alert_datetime >= %s"
                        params.append(start_date)
                    
                    if end_date:
                        query += " AND a.alert_datetime <= %s"
                        params.append(end_date)
                    
                    if alert_type:
                        query += " AND at.name = %s"
                        params.append(alert_type)
                    
                    query += " ORDER BY a.alert_datetime DESC LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                    
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Error fetching alerts: {str(e)}")
            return []
    
    def get_alert_by_id(self, alert_id):
        """
        Get a specific alert by ID
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT a.*, at.name as alert_type_name
                        FROM alerts a
                        LEFT JOIN alert_types at ON a.alert_type_id = at.id
                        WHERE a.id = %s
                    """, (alert_id,))
                    return cur.fetchone()
        except Exception as e:
            self.logger.error(f"Error fetching alert {alert_id}: {str(e)}")
            return None
