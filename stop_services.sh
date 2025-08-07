#!/bin/bash

# =========================================================
#  STOP ALL SERVICES - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  STOPPING YOLO POSE API SERVICES"
echo "==========================================================="

# Parse command line arguments
CLEAN=false

# Process command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --clean)
      CLEAN=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--clean]"
      echo "  --clean: Remove unused Docker resources after stopping"
      exit 1
      ;;
  esac
done

# Stop all running containers in this project
echo "Stopping all services..."
docker-compose down

echo "Services stopped successfully!"

# Clean up Docker resources if requested
if [ "$CLEAN" = true ]; then
    echo "Cleaning up unused Docker resources..."
    docker image prune -f
    docker container prune -f
    echo "Cleanup completed!"
fi

echo ""
echo "To completely clean up all Docker resources, use:"
echo "./clean_docker.sh all"
echo ""
echo "To start the services again, use:"
echo "./start_services.sh"
echo "==========================================================="
