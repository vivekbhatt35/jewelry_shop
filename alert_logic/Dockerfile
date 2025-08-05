# Stage 1: Build (install packages into /root/.local)
FROM python:3.12-slim AS builder
WORKDIR /app

# Install requirements and set permissions
COPY alert_logic/requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt && \
    chmod -R 777 /root/.local

# Stage 2: Minimal final image
FROM python:3.12-slim
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/output_image /app/logs && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser utils/ utils/
COPY --chown=appuser:appuser alert_logic/ alert_logic/
WORKDIR /app/alert_logic

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
EXPOSE 8012

USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8012"]
