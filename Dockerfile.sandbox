# ApexAurum Sandbox Container
# Optimized for Raspberry Pi 5 (ARM64)
# 
# Build: docker build -t apex-sandbox:latest .
# Test:  docker run --rm apex-sandbox:latest python -c "import numpy; print('OK')"

FROM python:3.11-slim-bookworm

LABEL maintainer="ApexAurum"
LABEL description="Isolated Python execution environment for AI agents"

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Python settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# Note: Keeping this minimal for Pi 5 memory constraints
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials for compiling Python packages
    build-essential \
    gcc \
    g++ \
    # For git-based pip installs
    git \
    # Network tools
    curl \
    wget \
    # Common libraries
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    # For Pillow/image processing
    libjpeg-dev \
    libpng-dev \
    # For matplotlib
    libfreetype6-dev \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages in layers (for better caching)
# Layer 1: Core scientific stack
RUN pip install \
    numpy \
    pandas \
    scipy

# Layer 2: Visualization
RUN pip install \
    matplotlib \
    seaborn \
    plotly

# Layer 3: ML basics (lighter packages for Pi)
RUN pip install \
    scikit-learn

# Layer 4: Web/Network
RUN pip install \
    requests \
    httpx \
    aiohttp \
    beautifulsoup4 \
    lxml

# Layer 5: Utilities
RUN pip install \
    pyyaml \
    python-dotenv \
    tqdm \
    pillow \
    python-dateutil \
    pytz

# Layer 6: Data formats
RUN pip install \
    openpyxl \
    xlsxwriter \
    python-docx \
    PyPDF2 \
    markdown

# Layer 7: Development tools
RUN pip install \
    pytest \
    black \
    isort \
    mypy

# Create non-root user for additional security (optional)
# Commented out - enable if you want extra isolation
# RUN useradd -m -s /bin/bash sandbox
# USER sandbox

# Create workspace directories
RUN mkdir -p /workspace /execution
WORKDIR /workspace

# Default command - can be overridden
CMD ["python"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1
