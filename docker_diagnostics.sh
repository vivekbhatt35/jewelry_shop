#!/bin/bash

# =========================================================
#  DOCKER DIAGNOSTICS SCRIPT
# =========================================================

echo "==========================================================="
echo "  DOCKER DIAGNOSTICS UTILITY"
echo "==========================================================="
echo "Running diagnostics to help troubleshoot Docker issues..."
echo ""

# Check Docker installation
echo "CHECKING DOCKER INSTALLATION:"
which docker || echo "Docker command not found in PATH"
docker --version || echo "Unable to get Docker version"
echo ""

# Check Docker daemon status
echo "CHECKING DOCKER DAEMON STATUS:"
if pgrep -x "Docker" > /dev/null || pgrep -f "com.docker.docker" > /dev/null; then
    echo "Docker process appears to be running"
else
    echo "Warning: No Docker processes found"
fi
echo ""

# Check Docker socket
echo "CHECKING DOCKER SOCKET:"
SOCKET_PATH="$HOME/.docker/run/docker.sock"
if [ -e "$SOCKET_PATH" ]; then
    echo "Docker socket exists at: $SOCKET_PATH"
    ls -la "$SOCKET_PATH"
else
    echo "Docker socket not found at expected location: $SOCKET_PATH"
    echo "Alternative socket locations:"
    ls -la /var/run/docker.sock 2>/dev/null || echo "- /var/run/docker.sock not found"
fi
echo ""

# Check Docker environment variables
echo "CHECKING DOCKER ENVIRONMENT:"
echo "DOCKER_HOST: ${DOCKER_HOST:-Not set}"
echo "DOCKER_CONFIG: ${DOCKER_CONFIG:-Not set}"
echo ""

# Test Docker connectivity
echo "TESTING DOCKER CONNECTIVITY:"
timeout 5 docker info > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Docker daemon is responding correctly"
else
    echo "Error: Cannot connect to Docker daemon"
    docker info 2>&1 | head -5
    echo "..."
fi
echo ""

# Check disk space
echo "CHECKING DISK SPACE:"
df -h | grep -E "Filesystem|/$"
echo ""

# Provide recovery steps
echo "==========================================================="
echo "RECOVERY STEPS FOR COMMON ISSUES:"
echo ""
echo "1. For 'context canceled' or socket issues:"
echo "   - Restart Docker Desktop completely"
echo "   - If using macOS: quit Docker from menu bar and restart"
echo ""
echo "2. For permission issues:"
echo "   - Check permissions: ls -la $HOME/.docker/run/"
echo "   - Try restarting Docker Desktop with admin privileges"
echo ""
echo "3. For disk space issues:"
echo "   - Free up space: docker system prune -a"
echo "   - Check Docker Desktop settings for disk image location"
echo ""
echo "4. If all else fails:"
echo "   - Reset Docker: Docker Desktop → Troubleshoot → Reset to factory defaults"
echo "   - Reinstall Docker Desktop"
echo "==========================================================="
