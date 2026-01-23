#!/bin/bash
# ApexAurum Installer - Color and Logging Utilities
# Source this file: source setup/colors.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Unicode symbols
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
ARROW="${CYAN}→${NC}"
STAR="${YELLOW}★${NC}"
WARN="${YELLOW}⚠${NC}"
INFO="${BLUE}ℹ${NC}"
GEAR="${MAGENTA}⚙${NC}"

# Logging functions
log_info() {
    echo -e "${INFO} ${WHITE}$1${NC}"
}

log_success() {
    echo -e "${CHECK} ${GREEN}$1${NC}"
}

log_warning() {
    echo -e "${WARN} ${YELLOW}$1${NC}"
}

log_error() {
    echo -e "${CROSS} ${RED}$1${NC}"
}

log_step() {
    echo -e "${ARROW} ${CYAN}$1${NC}"
}

log_header() {
    echo ""
    echo -e "${BOLD}${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${WHITE}  $1${NC}"
    echo -e "${BOLD}${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

log_subheader() {
    echo ""
    echo -e "${BOLD}${CYAN}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BOLD}${WHITE}  $1${NC}"
    echo -e "${BOLD}${CYAN}───────────────────────────────────────────────────────────────${NC}"
}

# Progress spinner
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " ${CYAN}%c${NC}  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Run command with spinner
run_with_spinner() {
    local msg="$1"
    shift
    printf "${ARROW} ${CYAN}%s${NC}" "$msg"

    "$@" > /tmp/apex_install.log 2>&1 &
    local pid=$!
    spinner $pid
    wait $pid
    local status=$?

    if [ $status -eq 0 ]; then
        echo -e " ${CHECK}"
        return 0
    else
        echo -e " ${CROSS}"
        echo -e "${DIM}$(cat /tmp/apex_install.log | tail -5)${NC}"
        return 1
    fi
}

# Ask yes/no question
ask_yes_no() {
    local question="$1"
    local default="${2:-n}"

    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    echo -ne "${INFO} ${WHITE}$question${NC} ${DIM}$prompt${NC} "
    read -r answer

    if [ -z "$answer" ]; then
        answer="$default"
    fi

    case "$answer" in
        [Yy]*) return 0 ;;
        *) return 1 ;;
    esac
}

# Print key-value pair
print_kv() {
    local key="$1"
    local value="$2"
    local status="${3:-}"

    printf "  ${DIM}%-20s${NC} " "$key:"
    if [ -n "$status" ]; then
        if [ "$status" = "ok" ]; then
            echo -e "${GREEN}$value${NC}"
        elif [ "$status" = "warn" ]; then
            echo -e "${YELLOW}$value${NC}"
        elif [ "$status" = "error" ]; then
            echo -e "${RED}$value${NC}"
        else
            echo -e "${WHITE}$value${NC}"
        fi
    else
        echo -e "${WHITE}$value${NC}"
    fi
}
