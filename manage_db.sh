#!/bin/bash

# =========================================================
#  DATABASE MANAGEMENT SCRIPT - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  DATABASE MANAGEMENT SCRIPT"
echo "==========================================================="

function show_help {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status        Show database container status"
    echo "  init          Initialize the database (run initial setup)"
    echo "  backup        Backup the database to a file"
    echo "  restore FILE  Restore the database from a backup file"
    echo "  psql          Start a PostgreSQL shell"
    echo "  help          Show this help message"
    echo ""
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or not accessible"
    exit 1
fi

# Command handling
case "$1" in
    status)
        echo "Checking database status..."
        docker-compose ps db
        ;;
        
    init)
        echo "Initializing database..."
        # Make sure the database container is running
        if ! docker-compose ps | grep -q "db.*Up"; then
            echo "Starting database container..."
            docker-compose up -d db
            echo "Waiting for database to initialize..."
            sleep 10
        fi
        
        # Check if init script exists
        if [ ! -f "database/init.sql" ]; then
            echo "Error: Database initialization script not found at database/init.sql"
            exit 1
        fi
        
        # Execute the initialization script inside the container
        echo "Running initialization script..."
        docker-compose exec db psql -U postgres -d camera_system -f /docker-entrypoint-initdb.d/init.sql
        echo "Database initialization completed"
        ;;
        
    backup)
        echo "Backing up database..."
        BACKUP_FILE="camera_system_backup_$(date +%Y%m%d_%H%M%S).sql"
        docker-compose exec db pg_dump -U postgres camera_system > "$BACKUP_FILE"
        echo "Backup saved to: $BACKUP_FILE"
        ;;
        
    restore)
        if [ -z "$2" ]; then
            echo "Error: Backup file not specified"
            echo "Usage: $0 restore BACKUP_FILE"
            exit 1
        fi
        
        if [ ! -f "$2" ]; then
            echo "Error: Backup file not found: $2"
            exit 1
        fi
        
        echo "Restoring database from: $2"
        cat "$2" | docker-compose exec -T db psql -U postgres camera_system
        echo "Database restore completed"
        ;;
        
    psql)
        echo "Starting PostgreSQL shell..."
        docker-compose exec db psql -U postgres camera_system
        ;;
        
    help|*)
        show_help
        ;;
esac

echo "==========================================================="
