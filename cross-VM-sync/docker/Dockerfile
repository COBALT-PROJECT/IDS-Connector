FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt . 

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ids_sync_service.py .

# Create user, logs directory, and set permissions - ALL BEFORE switching user
RUN mkdir -p /app/logs && \
    useradd -m -u 1000 idsuser && \
    chown -R idsuser:idsuser /app

# Now switch to non-root user
USER idsuser

# Expose health check port
EXPOSE 8080

# Set environment variables with defaults
ENV PROVIDER_URL="" \
    CONSUMER_URL="" \
    IDS_USERNAME="admin" \
    IDS_PASSWORD="password" \
    POLL_INTERVAL_SECONDS="10" \
    MAX_RETRIES="3" \
    RETRY_BACKOFF_SECONDS="2" \
    HEALTH_PORT="8080" \
    CONNECTION_TIMEOUT="30" \
    LOG_LEVEL="INFO" \
    LOG_DIR="/app/logs"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run the application
CMD ["python", "-u", "ids_sync_service.py"]