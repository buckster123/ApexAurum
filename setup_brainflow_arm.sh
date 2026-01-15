#!/bin/bash
# Build BrainFlow from source for ARM64 (Raspberry Pi)
#
# This script builds native BrainFlow libraries for ARM64/aarch64,
# enabling full EEG functionality on Raspberry Pi.
#
# Usage: ./setup_brainflow_arm.sh
#
# Requirements:
# - Raspberry Pi with 64-bit OS
# - ~2GB free disk space
# - ~10-15 minutes build time on Pi 5

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Header
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}       ${GREEN}BrainFlow ARM64 Build Script${NC}                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   Build native EEG libraries for Raspberry Pi            ${BLUE}║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check architecture
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
    warn "This script is for ARM64. Detected: $ARCH"
    warn "On x86_64, the pip package works directly."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

info "Architecture: $ARCH"

# Check we're in the right directory
if [ ! -f "main.py" ] || [ ! -d "venv" ]; then
    error "Please run this script from the ApexAurum project root directory"
fi

# ============================================================================
# Step 1: Install build dependencies
# ============================================================================
info "Installing build dependencies..."

sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    libusb-1.0-0-dev \
    libbluetooth-dev \
    || error "Failed to install dependencies"

success "Build dependencies installed"

# ============================================================================
# Step 2: Clone BrainFlow
# ============================================================================
BRAINFLOW_DIR="/tmp/brainflow-build"

if [ -d "$BRAINFLOW_DIR" ]; then
    info "Removing existing brainflow build directory..."
    rm -rf "$BRAINFLOW_DIR"
fi

info "Cloning BrainFlow repository..."
git clone --depth 1 https://github.com/brainflow-dev/brainflow.git "$BRAINFLOW_DIR"
success "BrainFlow cloned"

# ============================================================================
# Step 3: Build native libraries
# ============================================================================
info "Building native libraries (this may take 10-15 minutes)..."
echo ""

cd "$BRAINFLOW_DIR"
mkdir -p build
cd build

# Configure with CMake
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_BLUETOOTH=ON \
    || error "CMake configuration failed"

# Build (use all cores)
CORES=$(nproc)
info "Building with $CORES cores..."
cmake --build . --parallel $CORES || error "Build failed"

success "Native libraries built"

# ============================================================================
# Step 4: Install to Python environment
# ============================================================================
cd "$BRAINFLOW_DIR"

info "Installing Python package..."

# Activate venv
source /home/llm/ApexAurum/venv/bin/activate

# First uninstall the pip version (has wrong arch libs)
pip uninstall -y brainflow 2>/dev/null || true

# Install from local build (use regular install, not editable)
cd python_package
pip install . || error "Python package installation failed"

success "BrainFlow installed to venv"

# ============================================================================
# Step 5: Copy native libraries
# ============================================================================
info "Copying native libraries to package..."

# Find where brainflow was installed
BRAINFLOW_PKG=$(python -c "import brainflow; import os; print(os.path.dirname(brainflow.__file__))")
LIB_DIR="$BRAINFLOW_PKG/lib"

# Copy the built libraries
cp "$BRAINFLOW_DIR/build/compiled/"*.so "$LIB_DIR/" 2>/dev/null || true
cp "$BRAINFLOW_DIR/build/compiled/"libBoardController* "$LIB_DIR/" 2>/dev/null || true
cp "$BRAINFLOW_DIR/build/compiled/"libDataHandler* "$LIB_DIR/" 2>/dev/null || true

# Make sure they're executable
chmod +x "$LIB_DIR/"*.so 2>/dev/null || true

success "Native libraries installed"

# ============================================================================
# Step 6: Verify installation
# ============================================================================
info "Verifying installation..."

cd /home/llm/ApexAurum

RESULT=$(./venv/bin/python -c "
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
params = BrainFlowInputParams()
board = BoardShim(BoardIds.SYNTHETIC_BOARD, params)
board.prepare_session()
board.start_stream()
import time
time.sleep(0.5)
data = board.get_current_board_data(100)
board.stop_stream()
board.release_session()
print(f'SUCCESS: Got {data.shape[1]} samples from synthetic board')
" 2>&1)

if [[ "$RESULT" == *"SUCCESS"* ]]; then
    success "$RESULT"
else
    warn "Verification had issues: $RESULT"
    warn "The build may still work - try running the EEG tools manually"
fi

# ============================================================================
# Cleanup (optional - keep if you want to rebuild later)
# ============================================================================
info "Build directory kept at: $BRAINFLOW_DIR"
info "You can delete it manually with: rm -rf $BRAINFLOW_DIR"
success "Setup complete"

# ============================================================================
# Done!
# ============================================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}         BrainFlow ARM64 Build Complete!                   ${GREEN}║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test it:${NC}"
echo "  source venv/bin/activate"
echo "  python -c \"from tools.eeg import eeg_connect; print(eeg_connect('', 'synthetic'))\""
echo ""
echo -e "${BLUE}The EEG tools should now use the real BrainFlow synthetic board${NC}"
echo -e "${BLUE}instead of the mock fallback.${NC}"
echo ""
