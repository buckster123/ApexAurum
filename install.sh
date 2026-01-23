#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       ApexAurum Installation Script                        ║
# ║                    Production-Grade AI Interface Installer                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   ./install.sh              Interactive installation menu
#   ./install.sh --streamlit  Direct Streamlit edition install
#   ./install.sh --fastapi    Direct FastAPI Lab edition install
#   ./install.sh --docker     Direct Docker setup
#   ./install.sh --detect     Show system detection only
#   ./install.sh --help       Show help
#

set -e

# Get script directory (works even if symlinked)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source modules
source setup/colors.sh
source setup/banner.sh
source setup/detect.sh
source setup/install_streamlit.sh
source setup/install_fastapi.sh
source setup/install_docker.sh

# ============================================================================
# Main Menu
# ============================================================================

show_menu() {
    show_banner
    show_version
    print_detection_summary
    print_recommendation

    echo -e "  ${BOLD}${WHITE}Select Installation:${NC}"
    echo ""
    echo -e "  ${CYAN}[1]${NC} Streamlit Edition     ${DIM}Full features, Claude API, 79+ tools${NC}"
    echo -e "  ${CYAN}[2]${NC} FastAPI Lab Edition   ${DIM}Lightweight, Local LLMs, REST API${NC}"
    echo -e "  ${CYAN}[3]${NC} Both Editions         ${DIM}Development setup${NC}"
    echo -e "  ${CYAN}[4]${NC} Docker Installation   ${DIM}Containerized deployment${NC}"
    echo ""
    echo -e "  ${DIM}[d] Detection details   [h] Help   [q] Quit${NC}"
    echo ""
}

show_help() {
    show_mini_banner
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./install.sh              Interactive installation menu"
    echo "  ./install.sh --streamlit  Direct Streamlit edition install"
    echo "  ./install.sh --fastapi    Direct FastAPI Lab edition install"
    echo "  ./install.sh --docker     Direct Docker setup"
    echo "  ./install.sh --detect     Show system detection only"
    echo ""
    echo -e "${BOLD}Editions:${NC}"
    echo ""
    echo -e "  ${CYAN}Streamlit Edition${NC}"
    echo "    Full-featured AI interface with Claude API"
    echo "    - 79+ integrated tools"
    echo "    - Multi-agent orchestration"
    echo "    - Village Protocol memory"
    echo "    - Music pipeline with Suno AI"
    echo "    - Group chat with parallel agents"
    echo "    Best for: Desktop use with Claude API"
    echo ""
    echo -e "  ${CYAN}FastAPI Lab Edition${NC}"
    echo "    Lightweight web UI for edge deployment"
    echo "    - REST API backend"
    echo "    - Local LLM support (Ollama)"
    echo "    - Hailo NPU acceleration"
    echo "    - Tool selector system"
    echo "    Best for: Raspberry Pi, local-only deployment"
    echo ""
    echo -e "  ${CYAN}Docker Edition${NC}"
    echo "    Containerized deployment option"
    echo "    - No system dependencies"
    echo "    - Isolated environment"
    echo "    - Easy updates"
    echo ""
    echo -e "${BOLD}Requirements:${NC}"
    echo "  - Python 3.10+"
    echo "  - For Streamlit: Anthropic API key"
    echo "  - For FastAPI Lab: Ollama or hailo-ollama"
    echo "  - For Docker: Docker installed and running"
    echo ""
}

# ============================================================================
# Parse Arguments
# ============================================================================

# Run detection first
run_detection

case "${1:-}" in
    --streamlit)
        show_mini_banner
        install_streamlit_edition
        show_completion_banner
        exit 0
        ;;
    --fastapi)
        show_mini_banner
        install_fastapi_edition
        show_completion_banner
        exit 0
        ;;
    --docker)
        show_mini_banner
        install_docker_edition
        show_completion_banner
        exit 0
        ;;
    --detect)
        show_mini_banner
        echo ""
        print_detection_summary
        print_recommendation
        exit 0
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
    "")
        # Interactive mode
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# ============================================================================
# Interactive Mode
# ============================================================================

while true; do
    show_menu

    echo -ne "  ${WHITE}Select [1-4, d, h, q]:${NC} "
    read -r choice

    case "$choice" in
        1)
            install_streamlit_edition
            show_completion_banner
            break
            ;;
        2)
            install_fastapi_edition
            show_completion_banner
            break
            ;;
        3)
            install_streamlit_edition
            install_fastapi_edition
            show_completion_banner
            break
            ;;
        4)
            install_docker_edition
            show_completion_banner
            break
            ;;
        d|D)
            clear
            show_mini_banner
            echo ""
            log_header "Detailed System Detection"

            print_kv "Platform" "$APEX_PLATFORM"
            print_kv "Is Raspberry Pi" "$APEX_IS_PI"
            print_kv "Pi Version" "${APEX_PI_VERSION:-N/A}"
            print_kv "Has Hailo NPU" "$APEX_HAS_HAILO"
            print_kv "Hailo Version" "${APEX_HAILO_VERSION:-N/A}"
            print_kv "Has Docker" "$APEX_HAS_DOCKER"
            print_kv "Docker Running" "$APEX_DOCKER_RUNNING"
            print_kv "Has Ollama" "$APEX_HAS_OLLAMA"
            print_kv "Ollama Type" "${APEX_OLLAMA_TYPE:-N/A}"
            print_kv "Python Version" "$APEX_PYTHON_VERSION"
            print_kv "Python OK (3.10+)" "$APEX_PYTHON_OK"

            echo ""
            echo -e "  ${DIM}Press Enter to continue...${NC}"
            read -r
            ;;
        h|H)
            clear
            show_help
            echo -e "  ${DIM}Press Enter to continue...${NC}"
            read -r
            ;;
        q|Q)
            echo ""
            log_info "Installation cancelled"
            exit 0
            ;;
        *)
            log_warning "Invalid choice. Please select 1-4, d, h, or q"
            sleep 1
            ;;
    esac
done
