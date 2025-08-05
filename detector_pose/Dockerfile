FROM python:3.12-slim-bookworm

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/output_image /app/logs /app/detector_pose/.config/Ultralytics && \
    chown -R appuser:appuser /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl ffmpeg libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY --chown=appuser:appuser detector_pose/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser detector_pose/ detector_pose/
COPY --chown=appuser:appuser utils/ utils/
WORKDIR /app/detector_pose

ENV PYTHONPATH=/app
ENV YOLO_CONFIG_DIR=/app/detector_pose/.config/Ultralytics
EXPOSE 8011

USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8011"]
