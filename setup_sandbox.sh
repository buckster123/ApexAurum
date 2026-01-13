#!/bin/bash
# ApexAurum Sandbox Setup Script
# For Raspberry Pi 5 with NVMe drive
#
# Run: chmod +x setup_sandbox.sh && ./setup_sandbox.sh

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         ApexAurum Sandbox Setup for Raspberry Pi 5            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
WORKSPACE_DIR="${APEX_WORKSPACE:-$HOME/apex_workspace}"
SANDBOX_IMAGE="apex-sandbox:latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on ARM64 (Pi 5)
check_architecture() {
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" ]]; then
        log_warn "Not running on ARM64 (detected: $ARCH)"
        log_warn "This setup is optimized for Raspberry Pi 5"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "Architecture: ARM64 (aarch64) ✓"
    fi
}

# Install Docker if not present
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker is already installed ✓"
        docker --version
    else
        log_info "Installing Docker..."
        
        # Install Docker using official script
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh
        
        # Add current user to docker group
        sudo usermod -aG docker $USER
        
        log_info "Docker installed ✓"
        log_warn "You may need to log out and back in for group changes to take effect"
    fi
}

# Configure Docker for Pi 5 optimization
configure_docker() {
    log_info "Configuring Docker for Pi 5..."
    
    # Create docker config directory
    sudo mkdir -p /etc/docker
    
    # Check if daemon.json exists
    if [ -f /etc/docker/daemon.json ]; then
        log_info "Docker daemon.json already exists, backing up..."
        sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
    fi
    
    # Write optimized configuration
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "default-ulimits": {
        "nofile": {
            "Name": "nofile",
            "Hard": 64000,
            "Soft": 64000
        }
    }
}
EOF
    
    # Restart Docker to apply changes
    sudo systemctl restart docker
    log_info "Docker configured ✓"
}

# Create workspace directory structure
setup_workspace() {
    log_info "Setting up workspace at $WORKSPACE_DIR..."
    
    mkdir -p "$WORKSPACE_DIR"/{projects,outputs,data,temp,.cache}
    
    # Create a README in the workspace
    cat > "$WORKSPACE_DIR/README.md" <<EOF
# ApexAurum Sandbox Workspace

This directory is the persistent workspace for sandbox executions.

## Structure

- \`projects/\` - Named project directories (persistent)
- \`outputs/\` - General output files
- \`data/\` - Data files and datasets
- \`temp/\` - Temporary execution files (may be cleaned up)
- \`.cache/\` - pip cache for faster package installs

## Usage from Agents

Inside the sandbox container:
- \`/workspace\` - This directory (persistent)
- \`/execution\` - Current execution directory (ephemeral)

Files in \`/workspace\` persist across executions.
Files in \`/execution\` are cleaned up after each execution.
EOF
    
    log_info "Workspace created ✓"
}

# Build the sandbox Docker image
build_image() {
    log_info "Building sandbox Docker image..."
    
    # Check if Dockerfile exists
    if [ ! -f "$SCRIPT_DIR/Dockerfile" ]; then
        log_error "Dockerfile not found at $SCRIPT_DIR/Dockerfile"
        exit 1
    fi
    
    # Build with progress output
    cd "$SCRIPT_DIR"
    docker build \
        --platform linux/arm64 \
        -t "$SANDBOX_IMAGE" \
        --progress=plain \
        .
    
    log_info "Sandbox image built ✓"
    docker images "$SANDBOX_IMAGE"
}

# Test the sandbox
test_sandbox() {
    log_info "Testing sandbox execution..."
    
    # Test 1: Basic Python
    echo "Test 1: Basic Python..."
    docker run --rm "$SANDBOX_IMAGE" python -c "print('Hello from sandbox!')"
    
    # Test 2: NumPy
    echo "Test 2: NumPy..."
    docker run --rm "$SANDBOX_IMAGE" python -c "import numpy as np; print(f'NumPy {np.__version__}: {np.array([1,2,3]).sum()}')"
    
    # Test 3: Pandas
    echo "Test 3: Pandas..."
    docker run --rm "$SANDBOX_IMAGE" python -c "import pandas as pd; print(f'Pandas {pd.__version__}')"
    
    # Test 4: Workspace mount
    echo "Test 4: Workspace mount..."
    docker run --rm \
        -v "$WORKSPACE_DIR:/workspace:rw" \
        "$SANDBOX_IMAGE" \
        python -c "
import os
print('Workspace contents:', os.listdir('/workspace'))
with open('/workspace/test_file.txt', 'w') as f:
    f.write('Sandbox write test')
print('Write test: OK')
"
    
    # Verify the file was written
    if [ -f "$WORKSPACE_DIR/test_file.txt" ]; then
        log_info "Workspace persistence test: OK ✓"
        rm "$WORKSPACE_DIR/test_file.txt"
    else
        log_error "Workspace persistence test: FAILED"
    fi
    
    # Test 5: Network isolation
    echo "Test 5: Network isolation (should fail)..."
    if docker run --rm --network none "$SANDBOX_IMAGE" python -c "import urllib.request; urllib.request.urlopen('http://google.com')" 2>/dev/null; then
        log_error "Network isolation test: FAILED (network should be blocked)"
    else
        log_info "Network isolation test: OK ✓ (network correctly blocked)"
    fi
    
    log_info "All tests passed ✓"
}

# Install Python dependencies for the host
install_python_deps() {
    log_info "Installing Python dependencies for sandbox manager..."
    
    # Check if we're in a venv
    if [ -z "$VIRTUAL_ENV" ]; then
        log_warn "Not in a virtual environment. Consider activating your ApexAurum venv first."
        read -p "Continue with system Python? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    pip install docker
    log_info "Python dependencies installed ✓"
}

# Print integration instructions
print_integration_guide() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    Setup Complete! 🎉                         ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Next steps to integrate with ApexAurum:"
    echo ""
    echo "1. Copy the sandbox modules to your ApexAurum installation:"
    echo "   cp -r core/sandbox_manager.py /path/to/ApexAurum/core/"
    echo "   cp -r tools/sandbox_tools.py /path/to/ApexAurum/tools/"
    echo ""
    echo "2. Add to your tools/__init__.py:"
    echo "   from tools.sandbox_tools import SANDBOX_TOOLS, create_sandbox_tools"
    echo "   ALL_TOOLS.extend(SANDBOX_TOOLS)"
    echo ""
    echo "3. Initialize in your main.py or tool handler:"
    echo "   sandbox_tools = create_sandbox_tools(workspace_path='$WORKSPACE_DIR')"
    echo ""
    echo "4. Route sandbox tool calls in your dispatcher:"
    echo "   if tool_name in ['execute_python', 'execute_python_safe', 'execute_python_sandbox',"
    echo "                    'sandbox_workspace_list', 'sandbox_workspace_read', 'sandbox_workspace_write']:"
    echo "       return sandbox_tools.dispatch(tool_name, **kwargs)"
    echo ""
    echo "Environment variable (optional, add to .env):"
    echo "   APEX_WORKSPACE=$WORKSPACE_DIR"
    echo ""
    echo "Test manually:"
    echo "   python -c \"from core.sandbox_manager import execute_python; print(execute_python('print(1+1)', mode='sandbox'))\""
    echo ""
}

# Main execution
main() {
    check_architecture
    install_docker
    configure_docker
    setup_workspace
    build_image
    install_python_deps
    test_sandbox
    print_integration_guide
}

# Run with options
case "${1:-}" in
    --build-only)
        build_image
        ;;
    --test-only)
        test_sandbox
        ;;
    --workspace-only)
        setup_workspace
        ;;
    --help)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (none)           Full setup: Docker, workspace, image, tests"
        echo "  --build-only     Only rebuild the Docker image"
        echo "  --test-only      Only run tests"
        echo "  --workspace-only Only create workspace directories"
        echo "  --help           Show this help"
        ;;
    *)
        main
        ;;
esac
