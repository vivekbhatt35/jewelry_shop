# PostgreSQL Database Integration

This document outlines the database structure and integration for the camera management system.

## Database Setup

A PostgreSQL database has been added to the system with the following tables:

1. `camera_configurations` - Stores camera settings and connection details
2. `alert_types` - Stores different types of alerts that can be detected
3. `alerts` - Stores alert events with references to images and metadata

## Database Schema

### Camera Configurations Table

```sql
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
```

### Alert Types Table

```sql
CREATE TABLE alert_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Alerts Table

```sql
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
```

## Integration Points

### Alert Logic Service

The Alert Logic service has been updated to:

1. Save detected alerts to the database
2. Provide endpoints to query alert history
3. Associate alerts with cameras

### Camera Manager Service

The Camera Manager service will be updated to:

1. Load camera configurations from the database
2. Generate configuration files from database entries
3. Provide endpoints to manage camera configurations

### UI Service

A new UI Service has been added that will:

1. Provide a web interface for managing cameras
2. Display alert history and images
3. Allow configuration of alert types and settings

## Configuration File Generation

The system will generate camera configuration files from the database entries. This ensures that:

1. Camera settings are centrally managed
2. Configuration changes can be made through a web interface
3. Multiple services can access the same configuration data

## Getting Started

1. Start the database and services:

```bash
docker-compose up -d
```

2. Test the database functionality:

```bash
./test_db.sh
```

3. Access the UI at http://localhost:3000
