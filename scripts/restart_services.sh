#!/bin/bash
echo "Stopping all containers..."
docker-compose down

echo "Waiting for containers to stop completely..."
sleep 5

echo "Starting all containers with new configuration..."
docker-compose up -d

echo "Waiting for services to initialize..."
sleep 10

echo "Services restarted with updated configuration."
