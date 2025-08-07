# Optimizing Database Storage

This document explains how the PostgreSQL database is configured to minimize disk space usage in this system.

## Current Configuration

The PostgreSQL database is configured with minimal settings to reduce its disk space footprint:

- Using PostgreSQL Alpine image (much smaller than standard image)
- Local storage directory instead of Docker volume
- Reduced shared buffer sizes and memory allocations
- Container memory limited to 200MB
- Performance settings optimized for low resource usage

## Disk Space Requirements

With the current configuration, the database will use:

- Initial size: ~40-60MB (after initialization)
- Expected growth: ~1KB per alert stored (including references)
- Estimated size for 10,000 alerts: ~50-100MB

## Managing Disk Space

To help manage disk space, we've provided a cleanup script:

```bash
./clean_db.sh [COMMAND]
```

Available commands:

- `size`: Show current database size and table sizes
- `vacuum`: Run VACUUM FULL to reclaim disk space
- `clean-logs`: Clean up database logs
- `reset`: Reset database to initial state (loses all data)

## Best Practices for Minimizing Space

1. **Regular Maintenance**:
   - Run `./clean_db.sh vacuum` periodically
   - This reclaims space from deleted rows

2. **Alert Data Management**:
   - Consider adding automatic purging of old alerts
   - Set up a policy for alert retention (e.g., 30 days)

3. **Image Management**:
   - Database stores only image paths, not images themselves
   - The image cleanup process is critical for overall disk usage

4. **Log Management**:
   - Run `./clean_db.sh clean-logs` to remove old logs
   - Database logs are separate from application logs

## Scaling Up

If you need more database capacity in the future:

1. Stop all services: `./stop_services.sh`
2. Edit `docker-compose.yml` to increase resource limits
3. Restart services: `./start_services.sh`

## Emergency Space Recovery

If disk space is critically low:

```bash
./clean_db.sh reset
```

**CAUTION**: This will delete all database data and start fresh.
