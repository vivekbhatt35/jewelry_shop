-- Create tables for camera management system

-- Camera alert types
CREATE TABLE alert_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Camera configurations
CREATE TABLE camera_configurations (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL UNIQUE,
    camera_name VARCHAR(100),
    camera_url VARCHAR(255) NOT NULL,
    camera_type VARCHAR(50),
    frame_interval INTEGER DEFAULT 1000,
    detection_enabled BOOLEAN DEFAULT TRUE,
    pose_enabled BOOLEAN DEFAULT TRUE,
    notify_enabled BOOLEAN DEFAULT TRUE,
    resolution VARCHAR(20) DEFAULT '1280x720',
    username VARCHAR(100),
    password VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts table
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL,
    alert_type_id INTEGER REFERENCES alert_types(id),
    alert_datetime TIMESTAMP NOT NULL,
    source_image_path VARCHAR(255),
    overlay_image_path VARCHAR(255),
    alert_image_path VARCHAR(255) NOT NULL,
    persons_count INTEGER DEFAULT 0,
    alert_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES camera_configurations(camera_id)
);

-- Insert default alert types
INSERT INTO alert_types (name, description) VALUES 
('Hands_Up', 'Person with hands raised above head'),
('Weapon', 'Person with detected weapon'),
('Face_Covered', 'Person with face covered');

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Create triggers to auto-update the updated_at column
CREATE TRIGGER update_camera_config_modtime
    BEFORE UPDATE ON camera_configurations
    FOR EACH ROW
    EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_alert_types_modtime
    BEFORE UPDATE ON alert_types
    FOR EACH ROW
    EXECUTE PROCEDURE update_modified_column();
