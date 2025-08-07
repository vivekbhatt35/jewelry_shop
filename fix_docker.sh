#!/bin/bash

# =========================================================
#  DOCKER DIAGNOSTICS AND FIX - YOLO POSE API
# =========================================================

echo "==========================================================="
echo "  DOCKER DIAGNOSTICS AND FIX SCRIPT"
echo "==========================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "✖️ Docker is not running or not accessible"
    
    # Check Docker Desktop process
    if pgrep -x "Docker" > /dev/null; then
        echo "✓ Docker Desktop application is running"
    else
        echo "✖️ Docker Desktop application is not running"
        echo "   Please start Docker Desktop and try again"
    fi
    
    # Check Docker socket
    if [ -S "$HOME/.docker/run/docker.sock" ]; then
        echo "✓ Docker socket file exists: $HOME/.docker/run/docker.sock"
        ls -la "$HOME/.docker/run/docker.sock"
    else
        echo "✖️ Docker socket file does not exist at $HOME/.docker/run/docker.sock"
    fi
else
    echo "✓ Docker is running and accessible"
fi

# Check docker-compose file syntax
echo ""
echo "Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    echo "✓ docker-compose.yml syntax is valid"
else
    echo "✖️ docker-compose.yml has syntax errors:"
    docker-compose config
fi

# Check for common issues in docker-compose.yml
echo ""
echo "Checking for common issues in docker-compose.yml..."

# Check volumes section
if grep -q "volumes: *$" docker-compose.yml; then
    echo "✖️ Empty 'volumes:' section found in docker-compose.yml"
    echo "   This needs to be fixed with proper formatting"
    
    # Offer to fix it
    read -p "Would you like to fix the empty volumes section? (y/n): " fix_volumes
    if [ "$fix_volumes" = "y" ]; then
        sed -i.bak 's/volumes: *$/volumes:\n  postgres_data: {}/' docker-compose.yml
        echo "✓ Fixed volumes section in docker-compose.yml"
        echo "   A backup was saved as docker-compose.yml.bak"
    fi
fi

# Check for space issues
echo ""
echo "Checking disk space..."
df -h | grep -E "Filesystem|/Users|/$"

# Run a basic test to see if Docker works
echo ""
echo "Running a simple Docker test..."
if docker run --rm hello-world > /dev/null 2>&1; then
    echo "✓ Docker container test successful!"
else
    echo "✖️ Unable to run test container"
    
    # Offer suggestions
    echo ""
    echo "Suggested fixes:"
    echo "1. Restart Docker Desktop"
    echo "2. Reset Docker Desktop to factory defaults:"
    echo "   - Click the Docker icon in the menu bar"
    echo "   - Select Troubleshoot > Reset to factory defaults"
    echo "3. Check if your Mac has enough disk space"
    echo "4. Check Docker Desktop logs:"
    echo "   ~/Library/Containers/com.docker.docker/Data/log/vm/dockerd.log"
fi

# Offer to try restarting services
echo ""
echo "Would you like to try starting services with the fixed configuration? (y/n): "
read restart_services

if [ "$restart_services" = "y" ]; then
    echo "Stopping any running services..."
    docker-compose down 2>/dev/null
    
    echo "Starting services with fixed configuration..."
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        echo "✓ Services started successfully!"
        docker-compose ps
    else
        echo "✖️ Service startup failed"
    fi
fi

echo "==========================================================="
echo "For more help, visit Docker's official troubleshooting guide:"
echo "https://docs.docker.com/desktop/troubleshoot/overview/"
echo "==========================================================="
