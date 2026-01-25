# ApexAurum Cloud - Production Dockerfile for Railway
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cache bust - change this to force rebuild of COPY and beyond
ARG CACHE_BUST=2026012504
RUN echo "Cache bust: $CACHE_BUST"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 apex && chown -R apex:apex /app
USER apex

# Railway uses PORT env variable
ENV PORT=8080
EXPOSE $PORT

# Railway handles healthchecks - removing Docker healthcheck to prevent startup race condition

# Start command with explicit logging
CMD ["sh", "-c", "echo 'Starting uvicorn...' && python -u -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info"]
