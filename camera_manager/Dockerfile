FROM python:3.12-slim-bookworm

WORKDIR /app

# Create non-root user and ensure directories have correct permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/output_image /app/logs /app/camera_manager/config && \
    chmod -R 777 /app/output_image /app/logs /app/camera_manager/config && \
    chown -R appuser:appuser /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY --chown=appuser:appuser camera_manager/requirements.txt requirements.txt
# Install numpy first to ensure correct version is used with OpenCV
RUN pip install --no-cache-dir 'numpy<2.0.0,>=1.23.5' && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser utils/ utils/
COPY --chown=appuser:appuser camera_manager/ camera_manager/
WORKDIR /app/camera_manager

ENV PYTHONPATH=/app
EXPOSE 8010

USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
