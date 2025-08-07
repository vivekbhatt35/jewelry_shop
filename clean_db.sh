#!/bin/bash

# =========================================================
#  DATABASE CLEANUP SCRIPT - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  DATABASE CLEANUP SCRIPT"
echo "==========================================================="

function show_help {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  size          Show current database size"
    echo "  vacuum        Run VACUUM FULL to reclaim disk space"
    echo "  clean-logs    Clean up database logs"
    echo "  reset         Reset database to initial state (CAUTION: loses all data)"
    echo "  help          Show this help message"
    echo ""
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or not accessible"
    exit 1
fi

# Check if database is running
if ! docker-compose ps | grep -q "db.*Up"; then
    echo "Error: Database container is not running"
    echo "Start it with: docker-compose up -d db"
    exit 1
fi

# Command handling
case "$1" in
    size)
        echo "Checking database size..."
        echo "Database directory size:"
        du -sh database/pgdata
        
        echo ""
        echo "Table sizes:"
        docker-compose exec db psql -U postgres -d camera_system -c "
        SELECT 
            table_name, 
            pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS total_size,
            pg_size_pretty(pg_relation_size(quote_ident(table_name))) AS data_size,
            pg_size_pretty(pg_total_relation_size(quote_ident(table_name)) - pg_relation_size(quote_ident(table_name))) AS external_size
        FROM 
            information_schema.tables
        WHERE 
            table_schema = 'public'
        ORDER BY 
            pg_total_relation_size(quote_ident(table_name)) DESC;
        "
        ;;
        
    vacuum)
        echo "Running VACUUM FULL to reclaim disk space..."
        docker-compose exec db psql -U postgres -d camera_system -c "VACUUM FULL;"
        echo "Vacuum completed."
        ;;
        
    clean-logs)
        echo "Cleaning PostgreSQL log files..."
        docker-compose exec db sh -c "find /var/lib/postgresql/data/pg_log -type f -name '*.log' -mtime +1 -delete"
        echo "Log cleanup completed."
        ;;
        
    reset)
        echo "CAUTION: This will reset the database and lose all data."
        read -p "Are you sure you want to continue? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "Operation cancelled."
            exit 0
        fi
        
        echo "Stopping all services..."
        docker-compose down
        
        echo "Removing database directory..."
        rm -rf database/pgdata
        mkdir -p database/pgdata
        
        echo "Starting database with fresh state..."
        docker-compose up -d db
        echo "Waiting for database to initialize..."
        sleep 10
        
        echo "Database reset completed."
        ;;
        
    help|*)
        show_help
        ;;
esac

echo "==========================================================="
