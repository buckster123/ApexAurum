#!/bin/bash
# ApexAurum Installer - Streamlit Edition
# Requires: colors.sh, detect.sh to be sourced first

install_streamlit_edition() {
    log_header "Installing Streamlit Edition"

    # Check Python
    if [ "$APEX_PYTHON_OK" != "true" ]; then
        log_error "Python 3.10+ is required. Found: $APEX_PYTHON_VERSION"
        return 1
    fi

    # Check system dependencies
    log_subheader "Checking System Dependencies"

    local missing_deps=()

    # Check for tesseract (OCR)
    if ! command -v tesseract &> /dev/null; then
        missing_deps+=("tesseract-ocr")
    else
        log_success "tesseract-ocr found"
    fi

    # Check for ffmpeg (audio/video)
    if ! command -v ffmpeg &> /dev/null; then
        missing_deps+=("ffmpeg")
    else
        log_success "ffmpeg found"
    fi

    # Check for fluidsynth (MIDI)
    if ! command -v fluidsynth &> /dev/null; then
        missing_deps+=("fluidsynth")
    else
        log_success "fluidsynth found"
    fi

    # Offer to install missing dependencies
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "Missing optional dependencies: ${missing_deps[*]}"
        echo -e "  ${DIM}These enable: OCR for PDFs, music pipeline, MIDI playback${NC}"

        if ask_yes_no "Install missing dependencies?" "y"; then
            if [ "$APEX_PLATFORM" = "linux" ] || [ "$APEX_IS_PI" = "true" ]; then
                log_step "Installing with apt..."
                sudo apt-get update -qq
                sudo apt-get install -y "${missing_deps[@]}"
            elif [ "$APEX_PLATFORM" = "macos" ]; then
                log_step "Installing with brew..."
                brew install "${missing_deps[@]}"
            fi
        else
            log_info "Skipping optional dependencies"
        fi
    fi

    # Create virtual environment
    log_subheader "Setting Up Python Environment"

    if [ -d "venv" ]; then
        log_warning "Virtual environment already exists"
        if ask_yes_no "Recreate it?" "n"; then
            rm -rf venv
        else
            log_info "Using existing venv"
        fi
    fi

    if [ ! -d "venv" ]; then
        run_with_spinner "Creating virtual environment..." python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Upgrade pip
    run_with_spinner "Upgrading pip..." pip install --upgrade pip wheel

    # Install requirements in stages
    log_subheader "Installing Python Packages"

    echo -e "  ${DIM}This may take a few minutes...${NC}"
    echo ""

    # Core packages first
    run_with_spinner "Installing core packages..." pip install streamlit anthropic python-dotenv

    # Vector/ML packages
    run_with_spinner "Installing ML packages..." pip install chromadb sentence-transformers

    # Full requirements
    run_with_spinner "Installing remaining packages..." pip install -r requirements.txt

    # Setup environment file
    log_subheader "Configuration"

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env from template"
        else
            # Create minimal .env
            cat > .env << 'EOF'
# ApexAurum Configuration
# Get your API key at: https://console.anthropic.com/

ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Enhanced embeddings
# VOYAGE_API_KEY=pa-...

# Optional: Music generation
# SUNO_API_KEY=...

# Model settings
DEFAULT_MODEL=claude-sonnet-4-5-20251022
MAX_TOKENS=64000
EOF
            log_success "Created .env template"
        fi

        log_warning "Please edit .env and add your ANTHROPIC_API_KEY"
    else
        log_info ".env already exists"
    fi

    # Create required directories
    mkdir -p sandbox/music sandbox/midi sandbox/datasets
    log_success "Created sandbox directories"

    # Verify installation
    log_subheader "Verification"

    echo -e "  ${DIM}Checking installation...${NC}"

    # Check tool count
    local tool_count=$(python3 -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))" 2>/dev/null)
    if [ -n "$tool_count" ]; then
        print_kv "Tools loaded" "$tool_count" "ok"
    else
        print_kv "Tools loaded" "Import error" "error"
    fi

    # Check imports
    if python3 -c "from core import ClaudeAPIClient" 2>/dev/null; then
        print_kv "Core modules" "OK" "ok"
    else
        print_kv "Core modules" "Import error" "error"
    fi

    # Done
    log_success "Streamlit Edition installed successfully!"
    echo ""
    echo -e "  ${BOLD}To start:${NC}"
    echo -e "    ${CYAN}source venv/bin/activate${NC}"
    echo -e "    ${CYAN}streamlit run main.py${NC}"
    echo ""
    echo -e "  ${DIM}Then open: http://localhost:8501${NC}"
}
