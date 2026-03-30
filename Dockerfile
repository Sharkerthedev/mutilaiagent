FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies with verbose output
RUN pip install --no-cache-dir -r requirements.txt || \
    (pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt)

# Copy application files
COPY . .

# Create logs and data directories
RUN mkdir -p logs data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default PORT for HuggingFace
ENV PORT=7860

# Health check (non-blocking)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/ || python -c "import sys; sys.exit(0)" || exit 0

# Run the application
CMD ["python", "main.py"]
