# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV and EasyOCR (minimal set)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations for smaller size
RUN pip install --no-cache-dir --disable-pip-version-check \
    --find-links https://download.pytorch.org/whl/cpu/torch_stable.html \
    -r requirements.txt \
    && pip cache purge \
    && find /usr/local/lib/python3.11 -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy only necessary application files
COPY *.py ./
COPY static/ ./static/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TORCH_HOME=/tmp
ENV CUDA_VISIBLE_DEVICES=""

# Create non-root user with home directory for EasyOCR models
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Set EasyOCR model directory to writable location
ENV EASYOCR_MODULE_PATH=/home/app/.EasyOCR

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]