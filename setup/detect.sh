#!/bin/bash
# ApexAurum Installer - Platform Detection
# Source this file: source setup/detect.sh

# Detection results (exported for other scripts)
export APEX_PLATFORM=""        # linux, macos, windows (wsl)
export APEX_IS_PI=""           # true/false
export APEX_PI_VERSION=""      # 4, 5, or empty
export APEX_HAS_HAILO=""       # true/false
export APEX_HAILO_VERSION=""   # 8L, 10H, or empty
export APEX_HAS_DOCKER=""      # true/false
export APEX_DOCKER_RUNNING=""  # true/false
export APEX_HAS_OLLAMA=""      # true/false
export APEX_OLLAMA_TYPE=""     # standard, hailo, or empty
export APEX_PYTHON_VERSION=""  # e.g., 3.11.2
export APEX_PYTHON_OK=""       # true/false (3.10+ required)

detect_platform() {
    case "$(uname -s)" in
        Linux*)
            if grep -q Microsoft /proc/version 2>/dev/null; then
                APEX_PLATFORM="wsl"
            else
                APEX_PLATFORM="linux"
            fi
            ;;
        Darwin*)
            APEX_PLATFORM="macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            APEX_PLATFORM="windows"
            ;;
        *)
            APEX_PLATFORM="unknown"
            ;;
    esac
}

detect_raspberry_pi() {
    APEX_IS_PI="false"
    APEX_PI_VERSION=""

    if [ -f /proc/device-tree/model ]; then
        # Use tr to remove null bytes (common in device-tree)
        local model=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
        if [[ "$model" == *"Raspberry Pi"* ]]; then
            APEX_IS_PI="true"
            if [[ "$model" == *"Pi 5"* ]]; then
                APEX_PI_VERSION="5"
            elif [[ "$model" == *"Pi 4"* ]]; then
                APEX_PI_VERSION="4"
            elif [[ "$model" == *"Pi 3"* ]]; then
                APEX_PI_VERSION="3"
            fi
        fi
    fi
}

detect_hailo() {
    APEX_HAS_HAILO="false"
    APEX_HAILO_VERSION=""

    # Check for Hailo device
    if [ -e /dev/hailo0 ]; then
        APEX_HAS_HAILO="true"

        # Try lspci first (most reliable)
        if command -v lspci &> /dev/null; then
            local pci_info=$(lspci 2>/dev/null | grep -i hailo)
            if [[ "$pci_info" == *"Hailo-10H"* ]]; then
                APEX_HAILO_VERSION="10H"
            elif [[ "$pci_info" == *"Hailo-8L"* ]]; then
                APEX_HAILO_VERSION="8L"
            elif [[ "$pci_info" == *"Hailo-8"* ]]; then
                APEX_HAILO_VERSION="8"
            fi
        fi

        # Fallback: try hailortcli
        if [ -z "$APEX_HAILO_VERSION" ] && command -v hailortcli &> /dev/null; then
            local info=$(hailortcli fw-control identify 2>/dev/null)
            if [[ "$info" == *"HAILO-10H"* ]] || [[ "$info" == *"hailo10h"* ]]; then
                APEX_HAILO_VERSION="10H"
            elif [[ "$info" == *"HAILO-8L"* ]] || [[ "$info" == *"hailo8l"* ]]; then
                APEX_HAILO_VERSION="8L"
            elif [[ "$info" == *"HAILO-8"* ]] || [[ "$info" == *"hailo8"* ]]; then
                APEX_HAILO_VERSION="8"
            fi
        fi

        # Final fallback: assume 10H if hailo-ollama exists
        if [ -z "$APEX_HAILO_VERSION" ]; then
            if systemctl list-unit-files hailo-ollama.service &>/dev/null; then
                APEX_HAILO_VERSION="10H"
            else
                APEX_HAILO_VERSION="detected"
            fi
        fi
    fi
}

detect_docker() {
    APEX_HAS_DOCKER="false"
    APEX_DOCKER_RUNNING="false"

    if command -v docker &> /dev/null; then
        APEX_HAS_DOCKER="true"

        # Check if Docker daemon is running
        if docker info &> /dev/null; then
            APEX_DOCKER_RUNNING="true"
        fi
    fi
}

detect_ollama() {
    APEX_HAS_OLLAMA="false"
    APEX_OLLAMA_TYPE=""

    # Check for hailo-ollama first (takes precedence)
    if systemctl is-active --quiet hailo-ollama 2>/dev/null; then
        APEX_HAS_OLLAMA="true"
        APEX_OLLAMA_TYPE="hailo"
        return
    fi

    # Check for standard Ollama
    if command -v ollama &> /dev/null; then
        APEX_HAS_OLLAMA="true"
        APEX_OLLAMA_TYPE="standard"
        return
    fi

    # Check if Ollama is running on default port
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        APEX_HAS_OLLAMA="true"
        APEX_OLLAMA_TYPE="standard"
    fi
}

detect_python() {
    APEX_PYTHON_VERSION=""
    APEX_PYTHON_OK="false"

    # Try python3 first
    if command -v python3 &> /dev/null; then
        APEX_PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    elif command -v python &> /dev/null; then
        APEX_PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
    fi

    if [ -n "$APEX_PYTHON_VERSION" ]; then
        # Check if version is 3.10+
        local major=$(echo "$APEX_PYTHON_VERSION" | cut -d. -f1)
        local minor=$(echo "$APEX_PYTHON_VERSION" | cut -d. -f2)

        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            APEX_PYTHON_OK="true"
        fi
    fi
}

# Run all detections
run_detection() {
    detect_platform
    detect_raspberry_pi
    detect_hailo
    detect_docker
    detect_ollama
    detect_python
}

# Print detection summary
print_detection_summary() {
    log_subheader "System Detection"

    # Platform
    local platform_display=""
    case "$APEX_PLATFORM" in
        linux) platform_display="Linux" ;;
        macos) platform_display="macOS" ;;
        wsl) platform_display="Windows (WSL)" ;;
        windows) platform_display="Windows" ;;
        *) platform_display="Unknown" ;;
    esac
    print_kv "Platform" "$platform_display" "ok"

    # Raspberry Pi
    if [ "$APEX_IS_PI" = "true" ]; then
        print_kv "Raspberry Pi" "Pi $APEX_PI_VERSION detected" "ok"
    fi

    # Hailo
    if [ "$APEX_HAS_HAILO" = "true" ]; then
        local hailo_text="Hailo-$APEX_HAILO_VERSION NPU"
        print_kv "AI Accelerator" "$hailo_text" "ok"
    fi

    # Python
    if [ "$APEX_PYTHON_OK" = "true" ]; then
        print_kv "Python" "$APEX_PYTHON_VERSION" "ok"
    elif [ -n "$APEX_PYTHON_VERSION" ]; then
        print_kv "Python" "$APEX_PYTHON_VERSION (3.10+ required)" "error"
    else
        print_kv "Python" "Not found" "error"
    fi

    # Docker
    if [ "$APEX_HAS_DOCKER" = "true" ]; then
        if [ "$APEX_DOCKER_RUNNING" = "true" ]; then
            print_kv "Docker" "Available & running" "ok"
        else
            print_kv "Docker" "Installed (daemon not running)" "warn"
        fi
    else
        print_kv "Docker" "Not installed" ""
    fi

    # Ollama
    if [ "$APEX_HAS_OLLAMA" = "true" ]; then
        if [ "$APEX_OLLAMA_TYPE" = "hailo" ]; then
            print_kv "LLM Backend" "hailo-ollama (NPU accelerated)" "ok"
        else
            print_kv "LLM Backend" "Ollama (standard)" "ok"
        fi
    else
        print_kv "LLM Backend" "Not detected" ""
    fi

    echo ""
}

# Get recommendation based on detection
get_recommendation() {
    if [ "$APEX_IS_PI" = "true" ] && [ "$APEX_HAS_HAILO" = "true" ]; then
        echo "fastapi"
        return
    fi

    if [ "$APEX_IS_PI" = "true" ]; then
        echo "fastapi"
        return
    fi

    echo "streamlit"
}

print_recommendation() {
    local rec=$(get_recommendation)

    echo -e "  ${STAR} ${BOLD}${WHITE}Recommended:${NC} "

    case "$rec" in
        fastapi)
            echo -e "     ${CYAN}FastAPI Lab Edition${NC}"
            echo -e "     ${DIM}Optimized for edge deployment with local LLMs${NC}"
            if [ "$APEX_HAS_HAILO" = "true" ]; then
                echo -e "     ${DIM}Will use Hailo-$APEX_HAILO_VERSION NPU acceleration${NC}"
            fi
            ;;
        streamlit)
            echo -e "     ${CYAN}Streamlit Edition${NC}"
            echo -e "     ${DIM}Full features with Claude API integration${NC}"
            ;;
    esac
    echo ""
}
