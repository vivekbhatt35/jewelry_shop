FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl ffmpeg libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY detector_pose/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY detector_pose/ detector_pose/
COPY utils/ utils/
WORKDIR /app/detector_pose

ENV PYTHONPATH=/app
EXPOSE 8011

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8011"]
