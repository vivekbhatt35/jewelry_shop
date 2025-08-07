#!/bin/bash

# =========================================================
#  DOCKER SOCKET REPAIR SCRIPT - MACOS
# =========================================================

echo "==========================================================="
echo "  DOCKER SOCKET REPAIR UTILITY"
echo "==========================================================="
echo "This script attempts to fix common Docker socket issues on macOS"
echo ""

# Detect macOS
if [ "$(uname)" != "Darwin" ]; then
    echo "Error: This script is designed for macOS only"
    echo "For other platforms, please refer to Docker's documentation"
    exit 1
fi

# Check Docker Desktop installation
DOCKER_APP="/Applications/Docker.app"
if [ ! -d "$DOCKER_APP" ]; then
    echo "Error: Docker Desktop not found at $DOCKER_APP"
    echo "Please ensure Docker Desktop is properly installed"
    exit 1
fi

# Check if Docker is running
if pgrep -x "Docker" > /dev/null || pgrep -f "com.docker.docker" > /dev/null; then
    echo "Docker process is running"
else
    echo "Docker Desktop is not running. Attempting to start..."
    open -a Docker
    echo "Waiting for Docker to start up (30 seconds)..."
    sleep 30
fi

# Check socket locations
SOCKET_PATHS=(
    "$HOME/.docker/run/docker.sock"
    "/var/run/docker.sock"
)

FOUND_SOCKET=false
for SOCKET in "${SOCKET_PATHS[@]}"; do
    if [ -e "$SOCKET" ]; then
        echo "Found Docker socket at: $SOCKET"
        FOUND_SOCKET=true
        SOCKET_PATH=$SOCKET
    fi
done

if [ "$FOUND_SOCKET" = false ]; then
    echo "Warning: Could not find Docker socket at standard locations"
fi

# Check Docker Desktop context
echo "Checking Docker Desktop context..."
mkdir -p $HOME/.docker/contexts/meta
if [ ! -f "$HOME/.docker/contexts/meta/37eab29c8e1d8338d9ed3ab2c9fac0f055c4c5ac789ed84ec45eb8f9fb4a9534/meta.json" ]; then
    echo "Docker context metadata may be missing or corrupted"
else
    echo "Docker context metadata exists"
fi

# Attempt to restart Docker service
echo "Attempting to restart Docker service..."
echo "Quitting Docker Desktop..."
osascript -e 'quit app "Docker"'
sleep 5

echo "Removing any stale socket files..."
for SOCKET in "${SOCKET_PATHS[@]}"; do
    if [ -e "$SOCKET" ]; then
        echo "Removing stale socket: $SOCKET"
        rm -f "$SOCKET"
    fi
done

echo "Starting Docker Desktop..."
open -a Docker
echo "Waiting for Docker to initialize (45 seconds)..."
sleep 45

# Test Docker connection
echo "Testing Docker connection..."
if docker info > /dev/null 2>&1; then
    echo "Success! Docker is now accessible."
    docker --version
    echo ""
    echo "You can now run your Docker commands."
else
    echo "Error: Docker is still not accessible after repair attempt."
    echo ""
    echo "Advanced repair options:"
    echo "1. Reset Docker Desktop to factory defaults:"
    echo "   - Open Docker Desktop"
    echo "   - Click on the gear icon (Settings)"
    echo "   - Select 'Troubleshoot'"
    echo "   - Click 'Reset to factory defaults'"
    echo ""
    echo "2. Reinstall Docker Desktop:"
    echo "   - Uninstall Docker Desktop"
    echo "   - Delete ~/Library/Containers/com.docker.docker/"
    echo "   - Delete ~/Library/Application Support/Docker Desktop/"
    echo "   - Reinstall Docker Desktop from https://www.docker.com/products/docker-desktop/"
fi

echo "==========================================================="
