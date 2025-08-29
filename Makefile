# Makefile for YOLO Security Detection System

.PHONY: all build rebuild clean run stop logs restart verify update-model help

# Default target
all: help

# Build all services
build:
	@echo "Building all services..."
	docker-compose build

# Rebuild all services from scratch
rebuild:
	@echo "Rebuilding all services from scratch..."
	./rebuild_all.sh

# Clean all containers, volumes, and images
clean:
	@echo "Stopping all services..."
	docker-compose down
	@echo "Removing all related images..."
	docker images | grep yolo_pose_api | awk '{print $$3}' | xargs -I {} docker rmi {} || true
	@echo "Cleaning complete"

# Run all services
run:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started. Use 'make logs' to see logs"

# Stop all services
stop:
	@echo "Stopping all services..."
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Restart all services
restart: stop run

# Verify detector service configuration
verify:
	@echo "Verifying detector service configuration..."
	./verify_detector.sh

# Update model file
update-model:
	@if [ -z "$(MODEL_PATH)" ]; then \
		echo "Error: MODEL_PATH is required. Use: make update-model MODEL_PATH=/path/to/model.pt"; \
		exit 1; \
	fi
	@echo "Updating model with $(MODEL_PATH)..."
	./detector_detections/update_model.sh $(MODEL_PATH)

# Build and run only detector-detections service
detector:
	@echo "Building and running detector-detections service..."
	docker-compose build detector-detections
	docker-compose up -d detector-detections
	@echo "Detector service started. View logs with: docker-compose logs -f detector-detections"

# Help
help:
	@echo "YOLO Security Detection System Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make build           : Build all services"
	@echo "  make rebuild         : Rebuild all services from scratch"
	@echo "  make clean           : Clean all containers and images"
	@echo "  make run             : Start all services"
	@echo "  make stop            : Stop all services"
	@echo "  make logs            : View logs from all services"
	@echo "  make restart         : Restart all services"
	@echo "  make verify          : Verify detector service configuration"
	@echo "  make detector        : Build and run only the detector service"
	@echo "  make update-model MODEL_PATH=/path/to/model.pt : Update model file"
	@echo ""
