#!/bin/bash
# ApexAurum Installer - FastAPI Lab Edition
# Requires: colors.sh, detect.sh to be sourced first

install_fastapi_edition() {
    log_header "Installing FastAPI Lab Edition"

    # Check Python
    if [ "$APEX_PYTHON_OK" != "true" ]; then
        log_error "Python 3.10+ is required. Found: $APEX_PYTHON_VERSION"
        return 1
    fi

    local lab_dir="reusable_lib/scaffold/fastapi_app"

    # Check if lab exists
    if [ ! -d "$lab_dir" ]; then
        log_error "FastAPI Lab not found at $lab_dir"
        return 1
    fi

    # Create virtual environment
    log_subheader "Setting Up Python Environment"

    local venv_dir="$lab_dir/venv_lab"

    if [ -d "$venv_dir" ]; then
        log_warning "Virtual environment already exists"
        if ask_yes_no "Recreate it?" "n"; then
            rm -rf "$venv_dir"
        else
            log_info "Using existing venv"
        fi
    fi

    if [ ! -d "$venv_dir" ]; then
        run_with_spinner "Creating virtual environment..." python3 -m venv "$venv_dir"
    fi

    # Activate venv
    source "$venv_dir/bin/activate"

    # Upgrade pip
    run_with_spinner "Upgrading pip..." pip install --upgrade pip wheel

    # Install minimal requirements
    log_subheader "Installing Python Packages"

    run_with_spinner "Installing FastAPI packages..." pip install fastapi uvicorn python-dotenv httpx jinja2

    # If on Pi with Hailo, add sentence-transformers for embeddings
    if [ "$APEX_HAS_HAILO" = "true" ]; then
        run_with_spinner "Installing ML packages for Hailo..." pip install sentence-transformers chromadb
    fi

    # Setup LLM backend
    log_subheader "LLM Backend Configuration"

    if [ "$APEX_HAS_OLLAMA" = "true" ]; then
        if [ "$APEX_OLLAMA_TYPE" = "hailo" ]; then
            log_success "hailo-ollama detected - will use NPU acceleration"
            local provider="hailo-ollama"
            local base_url="http://localhost:11434"
        else
            log_success "Ollama detected"
            local provider="ollama"
            local base_url="http://localhost:11434"
        fi

        # List available models
        echo ""
        log_info "Available models:"
        if curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; [print(f'    - {m[\"name\"]}') for m in json.load(sys.stdin).get('models', [])]" 2>/dev/null; then
            :
        else
            echo "    (Could not fetch model list)"
        fi
        echo ""

    else
        log_warning "No LLM backend detected"
        echo ""
        echo -e "  ${DIM}Options:${NC}"
        echo -e "    ${CYAN}1.${NC} Install Ollama: curl -fsSL https://ollama.com/install.sh | sh"
        if [ "$APEX_IS_PI" = "true" ]; then
            echo -e "    ${CYAN}2.${NC} Use hailo-ollama for NPU acceleration"
        fi
        echo -e "    ${CYAN}3.${NC} Configure Claude API (edit .env with ANTHROPIC_API_KEY)"
        echo ""

        local provider="ollama"
        local base_url="http://localhost:11434"
    fi

    # Setup environment file
    log_subheader "Configuration"

    local env_file="$lab_dir/.env"

    if [ ! -f "$env_file" ]; then
        cat > "$env_file" << EOF
# FastAPI Lab Configuration
# LLM Provider: ollama, hailo-ollama, or anthropic
LLM_PROVIDER=$provider
OLLAMA_BASE_URL=$base_url
DEFAULT_MODEL=qwen2.5-instruct:1.5b

# Optional: For Claude API mode
# ANTHROPIC_API_KEY=sk-ant-...

# Server settings
HOST=0.0.0.0
PORT=8765
EOF
        log_success "Created .env configuration"
    else
        log_info ".env already exists"
    fi

    # Create sandbox directories
    mkdir -p "$lab_dir/sandbox"
    log_success "Created sandbox directory"

    # Create run script
    cat > "$lab_dir/run.sh" << 'EOF'
#!/bin/bash
# Quick start script for FastAPI Lab
cd "$(dirname "$0")"
source venv_lab/bin/activate
echo "Starting FastAPI Lab on http://localhost:8765"
uvicorn main:app --host 0.0.0.0 --port 8765 --reload
EOF
    chmod +x "$lab_dir/run.sh"
    log_success "Created run.sh launcher"

    # Verify installation
    log_subheader "Verification"

    if python3 -c "import fastapi, uvicorn" 2>/dev/null; then
        print_kv "FastAPI" "OK" "ok"
    else
        print_kv "FastAPI" "Import error" "error"
    fi

    if [ "$APEX_HAS_OLLAMA" = "true" ]; then
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            print_kv "LLM Backend" "Connected" "ok"
        else
            print_kv "LLM Backend" "Not responding" "warn"
        fi
    fi

    # Done
    log_success "FastAPI Lab Edition installed successfully!"
    echo ""
    echo -e "  ${BOLD}To start:${NC}"
    echo -e "    ${CYAN}cd $lab_dir${NC}"
    echo -e "    ${CYAN}./run.sh${NC}"
    echo ""
    echo -e "  ${DIM}Then open: http://localhost:8765${NC}"
    echo ""

    if [ "$APEX_HAS_HAILO" = "true" ]; then
        echo -e "  ${STAR} ${GREEN}Hailo-$APEX_HAILO_VERSION NPU will accelerate inference!${NC}"
        echo ""
    fi
}
