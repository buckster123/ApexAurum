#!/bin/bash
# ApexAurum Installer - ASCII Banner
# Source this file: source setup/banner.sh

show_banner() {
    # Clear screen for clean presentation
    clear

    echo -e "${YELLOW}"
    cat << 'EOF'

     █████╗ ██████╗ ███████╗██╗  ██╗ █████╗ ██╗   ██╗██████╗ ██╗   ██╗███╗   ███╗
    ██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██║   ██║██╔══██╗██║   ██║████╗ ████║
    ███████║██████╔╝█████╗   ╚███╔╝ ███████║██║   ██║██████╔╝██║   ██║██╔████╔██║
    ██╔══██║██╔═══╝ ██╔══╝   ██╔██╗ ██╔══██║██║   ██║██╔══██║██║   ██║██║╚██╔╝██║
    ██║  ██║██║     ███████╗██╔╝ ██╗██║  ██║╚██████╔╝██║  ██║╚██████╔╝██║ ╚═╝ ██║
    ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝

EOF
    echo -e "${NC}"
    echo -e "                    ${DIM}The Philosopher's Stone of AI Interfaces${NC}"
    echo -e "                       ${CYAN}79+ Tools${NC} · ${GREEN}Multi-Agent${NC} · ${MAGENTA}Edge AI${NC}"
    echo ""
}

show_mini_banner() {
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}  ${BOLD}${WHITE}ApexAurum${NC}  ${DIM}— Production-Grade AI Interface${NC}                   ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
}

show_completion_banner() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   ${BOLD}${WHITE}Installation Complete!${NC}                                     ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   ${DIM}\"From base metal to gold — the transmutation is complete.\"${NC}  ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

show_version() {
    local version="1.0-beta"
    local tools="79+"
    local agents="4 archetypes"

    echo -e "  ${DIM}Version:${NC}  ${WHITE}$version${NC}"
    echo -e "  ${DIM}Tools:${NC}    ${CYAN}$tools${NC}"
    echo -e "  ${DIM}Agents:${NC}   ${MAGENTA}$agents${NC}"
    echo ""
}
