#!/bin/bash

# =========================================================
#  STOP ALL SERVICES - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  STOPPING YOLO POSE API SERVICES"
echo "==========================================================="

# Stop all running containers in this project
echo "Stopping all services..."
docker-compose down

echo "Services stopped successfully!"
echo ""
echo "To completely clean up all resources (including images), use:"
echo "./scripts/cleanup_docker.sh"
echo ""
echo "To start the services again, use:"
echo "./start_services.sh"
echo "==========================================================="
