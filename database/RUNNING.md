# Running the Camera System with PostgreSQL Database

This guide explains how to run the camera system with the new PostgreSQL database integration.

## Prerequisites

- Docker and Docker Compose installed
- Model files in their respective directories:
  - `detector_pose/models/yolo11m-pose.pt`
  - `detector_detections/models/yolo11m.pt`

## Starting the System

1. Start all services using the provided script:

```bash
./start_services.sh
```

This script will:
- Create necessary directories
- Initialize the database
- Start all services in the correct order
- Wait for the database to be ready before starting dependent services

2. Verify that all services are running:

```bash
docker-compose ps
```

You should see the following services:
- `db` (PostgreSQL database)
- `camera-manager`
- `detector-pose`
- `detector-detections`
- `alert-logic`
- `ui-service` (if enabled)

## Database Management

A dedicated script is provided for database management:

```bash
./manage_db.sh [COMMAND]
```

Available commands:

- `status`: Check database container status
- `init`: Initialize or reset the database
- `backup`: Create a backup of the database
- `restore FILE`: Restore from a backup file
- `psql`: Start a PostgreSQL shell

## Configuration Flow

With the new database integration, camera configurations follow this flow:

1. Camera configurations are stored in the PostgreSQL database
2. The camera-manager service reads configurations from the database
3. Configuration files (*.cfg) are generated from database entries
4. Changes made via the UI or API are stored in the database

## API Endpoints

### Camera Manager API

- `GET /cameras`: List all cameras
- `GET /cameras/{camera_id}`: Get a specific camera
- `POST /cameras`: Create a new camera
- `PUT /cameras/{camera_id}`: Update a camera
- `DELETE /cameras/{camera_id}`: Delete a camera

### Alert Logic API

- `GET /alerts`: List all alerts with filtering options
- `GET /alerts/{alert_id}`: Get a specific alert
- `POST /alert`: Process an alert (internal use)
- `POST /cleanup`: Trigger image cleanup

## User Interface

The UI service provides a web interface for:

- Managing camera configurations
- Viewing alerts and alert history
- System monitoring

Access the UI at: http://localhost:3000

## Connection Details

- **PostgreSQL Database**:
  - Host: localhost (from host machine) or db (from containers)
  - Port: 5432
  - Username: postgres
  - Password: postgres
  - Database: camera_system

- **Camera Manager API**: http://localhost:8010
- **Alert Logic API**: http://localhost:8012
- **UI Service**: http://localhost:3000
