# Stage 1: Build (install packages into /root/.local)
FROM python:3.12-slim AS builder
WORKDIR /app

# Install requirements
COPY alert_logic/requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Minimal final image
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY utils/ utils/
COPY alert_logic/ alert_logic/
WORKDIR /app/alert_logic
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
EXPOSE 8012
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8012"]
