#!/bin/bash
# ApexAurum Installer - Docker Edition
# Requires: colors.sh, detect.sh to be sourced first

install_docker_edition() {
    log_header "Installing Docker Edition"

    # Check Docker
    if [ "$APEX_HAS_DOCKER" != "true" ]; then
        log_error "Docker is not installed"
        echo ""
        echo -e "  ${DIM}Install Docker:${NC}"
        echo -e "    ${CYAN}curl -fsSL https://get.docker.com | sh${NC}"
        echo ""
        return 1
    fi

    if [ "$APEX_DOCKER_RUNNING" != "true" ]; then
        log_error "Docker daemon is not running"
        echo ""
        echo -e "  ${DIM}Start Docker:${NC}"
        echo -e "    ${CYAN}sudo systemctl start docker${NC}"
        echo ""
        return 1
    fi

    log_success "Docker is ready"

    # Choose edition to containerize
    log_subheader "Select Edition"
    echo ""
    echo -e "  ${CYAN}[1]${NC} Streamlit Edition    ${DIM}Full features, Claude API${NC}"
    echo -e "  ${CYAN}[2]${NC} FastAPI Lab Edition  ${DIM}Lightweight, local LLMs${NC}"
    echo -e "  ${CYAN}[3]${NC} Both Editions        ${DIM}Complete stack${NC}"
    echo ""

    local choice
    while true; do
        echo -ne "  ${WHITE}Select [1-3]:${NC} "
        read -r choice
        case "$choice" in
            1) docker_edition="streamlit"; break ;;
            2) docker_edition="fastapi"; break ;;
            3) docker_edition="both"; break ;;
            *) echo -e "  ${RED}Invalid choice${NC}" ;;
        esac
    done

    # Setup environment
    log_subheader "Configuration"

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env from template"
        else
            cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-your-key-here
DEFAULT_MODEL=claude-sonnet-4-5-20251022
MAX_TOKENS=64000
EOF
            log_success "Created .env template"
        fi
        log_warning "Edit .env and add your API keys"
    fi

    # Build containers
    log_subheader "Building Containers"

    case "$docker_edition" in
        streamlit)
            run_with_spinner "Building Streamlit container..." \
                docker build -t apexaurum-streamlit -f Dockerfile .
            ;;
        fastapi)
            if [ -f "reusable_lib/scaffold/fastapi_app/Dockerfile" ]; then
                run_with_spinner "Building FastAPI container..." \
                    docker build -t apexaurum-fastapi -f reusable_lib/scaffold/fastapi_app/Dockerfile reusable_lib/scaffold/fastapi_app
            else
                # Create Dockerfile if missing
                create_fastapi_dockerfile
                run_with_spinner "Building FastAPI container..." \
                    docker build -t apexaurum-fastapi -f reusable_lib/scaffold/fastapi_app/Dockerfile reusable_lib/scaffold/fastapi_app
            fi
            ;;
        both)
            run_with_spinner "Building Streamlit container..." \
                docker build -t apexaurum-streamlit -f Dockerfile .
            if [ -f "reusable_lib/scaffold/fastapi_app/Dockerfile" ]; then
                run_with_spinner "Building FastAPI container..." \
                    docker build -t apexaurum-fastapi -f reusable_lib/scaffold/fastapi_app/Dockerfile reusable_lib/scaffold/fastapi_app
            fi
            ;;
    esac

    # Create docker-compose.local.yml
    log_subheader "Creating Docker Compose File"

    cat > docker-compose.local.yml << 'EOF'
version: '3.8'

services:
  streamlit:
    image: apexaurum-streamlit
    container_name: apexaurum-streamlit
    ports:
      - "8501:8501"
    volumes:
      - ./sandbox:/app/sandbox
      - ./.env:/app/.env:ro
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
    restart: unless-stopped
    profiles:
      - streamlit
      - full

  fastapi:
    image: apexaurum-fastapi
    container_name: apexaurum-fastapi
    ports:
      - "8765:8765"
    volumes:
      - ./reusable_lib/scaffold/fastapi_app/sandbox:/app/sandbox
    environment:
      - HOST=0.0.0.0
      - PORT=8765
    restart: unless-stopped
    profiles:
      - fastapi
      - full

  # Ollama for local LLM (optional)
  ollama:
    image: ollama/ollama
    container_name: apexaurum-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    profiles:
      - ollama
      - full

volumes:
  ollama_data:
EOF
    log_success "Created docker-compose.local.yml"

    # Done
    log_success "Docker setup complete!"
    echo ""
    echo -e "  ${BOLD}To start:${NC}"

    case "$docker_edition" in
        streamlit)
            echo -e "    ${CYAN}docker-compose -f docker-compose.local.yml --profile streamlit up${NC}"
            echo -e "    ${DIM}Then open: http://localhost:8501${NC}"
            ;;
        fastapi)
            echo -e "    ${CYAN}docker-compose -f docker-compose.local.yml --profile fastapi up${NC}"
            echo -e "    ${DIM}Then open: http://localhost:8765${NC}"
            ;;
        both)
            echo -e "    ${CYAN}docker-compose -f docker-compose.local.yml --profile full up${NC}"
            echo -e "    ${DIM}Streamlit: http://localhost:8501${NC}"
            echo -e "    ${DIM}FastAPI:   http://localhost:8765${NC}"
            ;;
    esac

    echo ""
}

create_fastapi_dockerfile() {
    cat > reusable_lib/scaffold/fastapi_app/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt* ./
RUN pip install --no-cache-dir fastapi uvicorn python-dotenv httpx jinja2

# Copy app
COPY . .

# Create sandbox
RUN mkdir -p sandbox

EXPOSE 8765

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
EOF
    log_info "Created FastAPI Dockerfile"
}
