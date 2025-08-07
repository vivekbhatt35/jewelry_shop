# Docker Troubleshooting Guide

## Common Docker Issues on macOS

### Issue: "Docker is not accessible" or "context canceled" errors

This issue commonly occurs on macOS when the Docker socket is not properly accessible. You may see errors like:

```
Get "http://%2FUsers%2Fvivek%2F.docker%2Frun%2Fdocker.sock/_ping": context canceled
```

### Quick Fix Steps

1. **Check Docker Desktop Status**
   - Look for the Docker whale icon in your menu bar
   - If it's there, make sure it shows "Docker Desktop is running"

2. **Restart Docker Desktop**
   - Click the Docker icon in menu bar
   - Select "Restart"
   - Wait 1-2 minutes for Docker to fully restart

3. **Use the Repair Script (for macOS)**
   ```bash
   ./fix_docker_macos.sh
   ```
   This script will:
   - Ensure Docker Desktop is running
   - Remove stale socket files
   - Restart Docker services
   - Test the connection

4. **Run Diagnostics**
   ```bash
   ./docker_diagnostics.sh
   ```
   This will:
   - Check Docker installation
   - Verify the Docker daemon status
   - Check socket paths and permissions
   - Test Docker connectivity

### Manual Fix Steps (if scripts don't work)

1. **Force Quit Docker Desktop**
   - Open Activity Monitor
   - Find "Docker" and "com.docker.backend" processes
   - Force quit these processes

2. **Delete Socket Files**
   ```bash
   rm -f $HOME/.docker/run/docker.sock
   rm -f /var/run/docker.sock 2>/dev/null
   ```

3. **Restart Docker Desktop**
   - Open Docker Desktop from Applications folder
   - Wait for it to fully initialize

4. **Reset Docker Desktop**
   - Open Docker Desktop preferences
   - Go to "Troubleshoot" section
   - Click "Reset to factory defaults"
   - Warning: This will remove all images and containers

### Permission Issues

If you see permission-related errors:

1. **Check Docker Socket Permissions**
   ```bash
   ls -la $HOME/.docker/run/
   ```

2. **Fix Permissions if Needed**
   ```bash
   sudo chmod 666 $HOME/.docker/run/docker.sock
   ```

### Socket Path Issues

If Docker is using a different socket path than expected:

1. **Set DOCKER_HOST Environment Variable**
   ```bash
   export DOCKER_HOST=unix:///var/run/docker.sock
   # or
   export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
   ```

2. **Add to Your Shell Profile**
   Add the export command to your `~/.zshrc` or `~/.bash_profile`

### Reinstallation (Last Resort)

If all else fails:

1. **Uninstall Docker Desktop**

2. **Clean Up Docker Files**
   ```bash
   rm -rf ~/Library/Containers/com.docker.docker/
   rm -rf ~/Library/Application\ Support/Docker\ Desktop/
   rm -rf ~/.docker/
   ```

3. **Reinstall Docker Desktop** from official website

## Using the Provided Scripts

### Docker Diagnostics Script
```bash
./docker_diagnostics.sh
```

### Docker Socket Repair Script (macOS only)
```bash
./fix_docker_macos.sh
```

### Docker Cleanup Script
```bash
./clean_docker.sh status
```

## Additional Resources

- [Docker Desktop for Mac Troubleshooting Guide](https://docs.docker.com/desktop/troubleshoot/overview/)
- [Docker Engine Troubleshooting](https://docs.docker.com/engine/troubleshoot/)
