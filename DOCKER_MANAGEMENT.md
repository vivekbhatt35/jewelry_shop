# Docker Image Management

This document explains how Docker images are managed in this project and how to avoid duplicate images taking up disk space.

## Understanding Docker Image Creation

By default, each time you run `docker-compose build`:

1. Docker creates new images for each service
2. Old images become "dangling" (untagged) but remain on disk
3. This can lead to significant disk space usage over time

## Managing Docker Images

### 1. Start Services Without Rebuilding

By default, the updated `start_services.sh` script now avoids rebuilding images unnecessarily:

```bash
# Use existing images (faster, no duplicates)
./start_services.sh

# Force a rebuild (when needed)
./start_services.sh --rebuild
```

### 2. Stop Services and Clean Up

The updated `stop_services.sh` script includes an option to clean up:

```bash
# Just stop services
./stop_services.sh

# Stop services and clean up unused resources
./stop_services.sh --clean
```

### 3. Check Docker Disk Usage

To see how much space Docker is using:

```bash
./docker_space.sh
```

This will show:
- Total disk usage
- Image sizes
- Container sizes
- Volume sizes

### 4. Clean Up Docker Resources

A dedicated script helps you clean up Docker resources:

```bash
# Show disk usage information
./clean_docker.sh status

# Remove unused containers, networks, and dangling images
./clean_docker.sh prune

# Remove only dangling images
./clean_docker.sh images

# Remove only stopped containers
./clean_docker.sh containers

# Full cleanup (removes all unused Docker resources)
./clean_docker.sh all
```

## Best Practices

1. **Avoid unnecessary rebuilds**:
   - Use `./start_services.sh` without `--rebuild` for regular usage
   - Only use `--rebuild` when you've made changes to Dockerfiles or dependencies

2. **Regular cleanup**:
   - Run `./stop_services.sh --clean` when stopping services
   - Periodically run `./clean_docker.sh prune` to free up space

3. **When disk space is critical**:
   - Run `./clean_docker.sh all` for a complete cleanup
   - Be aware you'll need to rebuild images the next time you start services

4. **Monitor disk usage**:
   - Use `./docker_space.sh` to check Docker disk usage
   - Look for large or duplicate images that could be removed
