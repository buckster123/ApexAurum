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

# Cache bust - change this to force rebuild
ARG CACHE_BUST=2026012401

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 apex && chown -R apex:apex /app
USER apex

# Railway uses PORT env variable
ENV PORT=8000
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Start command - Railway will override with $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
