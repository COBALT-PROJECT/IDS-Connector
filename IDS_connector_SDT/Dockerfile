# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY catalog_service.py .
COPY resource_service.py .
COPY file_extractor_service.py .
COPY ids_consumer_interface.py .
COPY manager.py .
COPY main.py .

# Copy .env file if it exists (for default values)
COPY .env* ./

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8004

# Run the application
CMD ["python", "main.py"]
