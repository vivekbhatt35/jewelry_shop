# Stage 1: Build dependencies
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY alert_logic/requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt && \
    chmod -R 777 /root/.local

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install runtime dependencies for OpenCV
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and ensure directories have correct permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/output_image /app/logs && \
    chmod -R 777 /app/output_image /app/logs && \
    chown -R appuser:appuser /app

# Copy dependencies from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser utils/ utils/
COPY --chown=appuser:appuser alert_logic/ alert_logic/
WORKDIR /app/alert_logic

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
EXPOSE 8012

USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8012"]
