#!/bin/bash

# Display Docker disk usage information
echo "==========================================================="
echo "  DOCKER DISK USAGE REPORT"
echo "==========================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or not accessible"
    exit 1
fi

# Show overall Docker disk usage
echo "OVERALL DISK USAGE:"
docker system df

echo ""
echo "IMAGES BY SIZE (largest first):"
docker images --format "{{.Repository}}:{{.Tag}} - {{.Size}}" | sort -k3 -hr

echo ""
echo "CONTAINERS:"
docker ps -a --size

echo ""
echo "VOLUMES:"
docker volume ls

echo ""
echo "To clean up unused resources, run:"
echo "./clean_docker.sh prune    # for basic cleanup"
echo "./clean_docker.sh all      # for complete cleanup"
echo "==========================================================="
