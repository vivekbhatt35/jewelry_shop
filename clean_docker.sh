#!/bin/bash

# =========================================================
#  DOCKER CLEANUP SCRIPT - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  DOCKER CLEANUP SCRIPT"
echo "==========================================================="

function show_help {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status       Show Docker disk usage"
    echo "  prune        Remove all unused containers, images, networks, and volumes"
    echo "  images       Remove only dangling images (no tag)"
    echo "  containers   Remove stopped containers"
    echo "  all          Run full cleanup (containers + images + volumes + build cache)"
    echo "  help         Show this help message"
    echo ""
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or not accessible"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if Docker Desktop is running (look for the whale icon in the menu bar)"
    echo "2. Try restarting Docker Desktop"
    echo "3. Check Docker socket path: $HOME/.docker/run/docker.sock"
    echo "4. On macOS, you might need to reset Docker Desktop:"
    echo "   - Click on Docker Desktop icon in the menu bar"
    echo "   - Select 'Troubleshoot'"
    echo "   - Choose 'Reset to factory defaults'"
    echo ""
    echo "Additional diagnostic information:"
    ps aux | grep -i docker | grep -v grep || echo "No Docker processes found"
    echo ""
    echo "Socket file check:"
    ls -la $HOME/.docker/run/ 2>/dev/null || echo "Docker socket directory not found"
    exit 1
fi

# Command handling
case "$1" in
    status)
        echo "Checking Docker disk usage..."
        docker system df
        
        echo ""
        echo "Listing images by size (largest first):"
        docker images --format "{{.Repository}}:{{.Tag}} - {{.Size}}" | sort -k3 -hr
        ;;
        
    prune)
        echo "Removing unused Docker resources..."
        docker system prune -f
        echo "Basic cleanup completed"
        ;;
        
    images)
        echo "Removing dangling images..."
        docker image prune -f
        echo "Image cleanup completed"
        
        echo "Current images:"
        docker images
        ;;
        
    containers)
        echo "Removing stopped containers..."
        docker container prune -f
        echo "Container cleanup completed"
        ;;
        
    all)
        echo "CAUTION: This will remove all unused Docker resources, including volumes."
        read -p "Are you sure you want to continue? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "Operation cancelled."
            exit 0
        fi
        
        echo "Stopping services..."
        docker-compose down
        
        echo "Performing full cleanup..."
        docker system prune -a --volumes -f
        
        echo "Full cleanup completed. You'll need to rebuild images next time you start services."
        ;;
        
    help|*)
        show_help
        ;;
esac

echo "==========================================================="
