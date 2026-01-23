# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       ApexAurum Installation Script                        ║
# ║                    Production-Grade AI Interface Installer                 ║
# ║                           Windows PowerShell                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   .\install.ps1              Interactive installation menu
#   .\install.ps1 -Edition streamlit  Direct Streamlit install
#   .\install.ps1 -Edition fastapi    Direct FastAPI Lab install
#   .\install.ps1 -Detect             Show system detection only
#

param(
    [string]$Edition = "",
    [switch]$Detect,
    [switch]$Help
)

# Colors
$script:Colors = @{
    Red     = "Red"
    Green   = "Green"
    Yellow  = "Yellow"
    Blue    = "Blue"
    Magenta = "Magenta"
    Cyan    = "Cyan"
    White   = "White"
    Gray    = "DarkGray"
}

function Write-ColorText {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color -NoNewline
}

function Write-Success { param([string]$Text) Write-Host "✓ $Text" -ForegroundColor Green }
function Write-Error { param([string]$Text) Write-Host "✗ $Text" -ForegroundColor Red }
function Write-Warning { param([string]$Text) Write-Host "⚠ $Text" -ForegroundColor Yellow }
function Write-Info { param([string]$Text) Write-Host "ℹ $Text" -ForegroundColor Cyan }
function Write-Step { param([string]$Text) Write-Host "→ $Text" -ForegroundColor Cyan }

function Show-Banner {
    Clear-Host
    Write-Host @"

     █████╗ ██████╗ ███████╗██╗  ██╗ █████╗ ██╗   ██╗██████╗ ██╗   ██╗███╗   ███╗
    ██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██║   ██║██╔══██╗██║   ██║████╗ ████║
    ███████║██████╔╝█████╗   ╚███╔╝ ███████║██║   ██║██████╔╝██║   ██║██╔████╔██║
    ██╔══██║██╔═══╝ ██╔══╝   ██╔██╗ ██╔══██║██║   ██║██╔══██║██║   ██║██║╚██╔╝██║
    ██║  ██║██║     ███████╗██╔╝ ██╗██║  ██║╚██████╔╝██║  ██║╚██████╔╝██║ ╚═╝ ██║
    ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝

"@ -ForegroundColor Yellow
    Write-Host "                    The Philosopher's Stone of AI Interfaces" -ForegroundColor DarkGray
    Write-Host "                       79+ Tools · Multi-Agent · Edge AI" -ForegroundColor Cyan
    Write-Host ""
}

function Get-SystemInfo {
    $info = @{
        Platform = "Windows"
        PythonVersion = ""
        PythonOK = $false
        HasDocker = $false
        DockerRunning = $false
        HasOllama = $false
        HasWSL = $false
    }

    # Check Python
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $info.PythonVersion = $Matches[0] -replace "Python ", ""
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            $info.PythonOK = ($major -ge 3 -and $minor -ge 10)
        }
    } catch {}

    # Check Docker
    $info.HasDocker = (Get-Command docker -ErrorAction SilentlyContinue) -ne $null
    if ($info.HasDocker) {
        try {
            $null = docker info 2>&1
            $info.DockerRunning = $?
        } catch {}
    }

    # Check Ollama
    $info.HasOllama = (Get-Command ollama -ErrorAction SilentlyContinue) -ne $null

    # Check WSL
    $info.HasWSL = (Get-Command wsl -ErrorAction SilentlyContinue) -ne $null

    return $info
}

function Show-Detection {
    $info = Get-SystemInfo

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  System Detection" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

    Write-Host "  Platform:            " -NoNewline -ForegroundColor DarkGray
    Write-Host "$($info.Platform)" -ForegroundColor Green

    Write-Host "  Python:              " -NoNewline -ForegroundColor DarkGray
    if ($info.PythonOK) {
        Write-Host "$($info.PythonVersion)" -ForegroundColor Green
    } elseif ($info.PythonVersion) {
        Write-Host "$($info.PythonVersion) (3.10+ required)" -ForegroundColor Red
    } else {
        Write-Host "Not found" -ForegroundColor Red
    }

    Write-Host "  Docker:              " -NoNewline -ForegroundColor DarkGray
    if ($info.HasDocker -and $info.DockerRunning) {
        Write-Host "Available & running" -ForegroundColor Green
    } elseif ($info.HasDocker) {
        Write-Host "Installed (not running)" -ForegroundColor Yellow
    } else {
        Write-Host "Not installed" -ForegroundColor DarkGray
    }

    Write-Host "  Ollama:              " -NoNewline -ForegroundColor DarkGray
    if ($info.HasOllama) {
        Write-Host "Available" -ForegroundColor Green
    } else {
        Write-Host "Not installed" -ForegroundColor DarkGray
    }

    Write-Host "  WSL:                 " -NoNewline -ForegroundColor DarkGray
    if ($info.HasWSL) {
        Write-Host "Available" -ForegroundColor Green
    } else {
        Write-Host "Not installed" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "  ★ " -NoNewline -ForegroundColor Yellow
    Write-Host "Recommended: " -ForegroundColor White -NoNewline
    if ($info.HasWSL) {
        Write-Host "Use WSL for full Linux experience" -ForegroundColor Cyan
    } else {
        Write-Host "Streamlit Edition (Docker recommended)" -ForegroundColor Cyan
    }
    Write-Host ""
}

function Install-StreamlitEdition {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  Installing Streamlit Edition" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host ""

    $info = Get-SystemInfo

    if (-not $info.PythonOK) {
        Write-Error "Python 3.10+ is required"
        Write-Host "  Download from: https://www.python.org/downloads/"
        return $false
    }

    # Check if venv exists
    if (Test-Path "venv") {
        Write-Warning "Virtual environment already exists"
    } else {
        Write-Step "Creating virtual environment..."
        python -m venv venv
        Write-Success "Virtual environment created"
    }

    # Activate venv
    Write-Step "Activating virtual environment..."
    & .\venv\Scripts\Activate.ps1

    # Install packages
    Write-Step "Installing packages (this may take a few minutes)..."
    pip install --upgrade pip -q
    pip install streamlit anthropic python-dotenv chromadb sentence-transformers -q
    pip install -r requirements.txt -q
    Write-Success "Packages installed"

    # Setup .env
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Success "Created .env from template"
        }
        Write-Warning "Edit .env and add your ANTHROPIC_API_KEY"
    }

    # Create directories
    New-Item -ItemType Directory -Force -Path "sandbox\music", "sandbox\midi", "sandbox\datasets" | Out-Null
    Write-Success "Created sandbox directories"

    # Verify
    try {
        $toolCount = python -c "from tools import ALL_TOOLS; print(len(ALL_TOOLS))"
        Write-Success "Installation verified: $toolCount tools loaded"
    } catch {
        Write-Warning "Could not verify installation"
    }

    Write-Host ""
    Write-Host "  To start:" -ForegroundColor White
    Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "    streamlit run main.py" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Then open: http://localhost:8501" -ForegroundColor DarkGray
    Write-Host ""

    return $true
}

function Show-Menu {
    Show-Banner
    Show-Detection

    Write-Host "  Select Installation:" -ForegroundColor White
    Write-Host ""
    Write-Host "  [1] Streamlit Edition     " -NoNewline -ForegroundColor Cyan
    Write-Host "Full features, Claude API, 79+ tools" -ForegroundColor DarkGray
    Write-Host "  [2] FastAPI Lab Edition   " -NoNewline -ForegroundColor Cyan
    Write-Host "Lightweight, Local LLMs, REST API" -ForegroundColor DarkGray
    Write-Host "  [3] Docker Installation   " -NoNewline -ForegroundColor Cyan
    Write-Host "Containerized deployment" -ForegroundColor DarkGray
    Write-Host "  [4] WSL Installation      " -NoNewline -ForegroundColor Cyan
    Write-Host "Full Linux experience on Windows" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [d] Detection details   [h] Help   [q] Quit" -ForegroundColor DarkGray
    Write-Host ""
}

function Show-Help {
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\install.ps1              Interactive installation menu"
    Write-Host "  .\install.ps1 -Edition streamlit  Direct Streamlit install"
    Write-Host "  .\install.ps1 -Edition fastapi    Direct FastAPI Lab install"
    Write-Host "  .\install.ps1 -Detect             Show system detection only"
    Write-Host ""
    Write-Host "For Windows, we recommend:" -ForegroundColor Yellow
    Write-Host "  1. WSL2 with Ubuntu for full Linux experience"
    Write-Host "  2. Docker Desktop for containerized deployment"
    Write-Host "  3. Native Python install with Streamlit Edition"
    Write-Host ""
}

function Show-Completion {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "║   Installation Complete!                                      ║" -ForegroundColor White
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "║   `"From base metal to gold - the transmutation is complete.`" ║" -ForegroundColor DarkGray
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
}

# Main
if ($Help) {
    Show-Help
    exit 0
}

if ($Detect) {
    Show-Banner
    Show-Detection
    exit 0
}

if ($Edition -eq "streamlit") {
    Show-Banner
    Install-StreamlitEdition
    Show-Completion
    exit 0
}

if ($Edition -eq "fastapi") {
    Write-Warning "FastAPI Lab is optimized for Linux/Pi. Consider using WSL or Docker."
    exit 0
}

# Interactive mode
while ($true) {
    Show-Menu
    $choice = Read-Host "  Select [1-4, d, h, q]"

    switch ($choice) {
        "1" {
            if (Install-StreamlitEdition) {
                Show-Completion
            }
            break
        }
        "2" {
            Write-Warning "FastAPI Lab is optimized for Linux/Pi."
            Write-Info "Consider option [4] WSL Installation for Linux experience on Windows."
            Read-Host "Press Enter to continue"
        }
        "3" {
            Write-Info "For Docker installation:"
            Write-Host "  1. Install Docker Desktop from https://docker.com"
            Write-Host "  2. Run: docker-compose up --build"
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "4" {
            Write-Info "For WSL installation:"
            Write-Host "  1. Enable WSL: wsl --install"
            Write-Host "  2. Restart Windows"
            Write-Host "  3. Open Ubuntu terminal"
            Write-Host "  4. Clone repo: git clone https://github.com/buckster123/ApexAurum.git"
            Write-Host "  5. Run: cd ApexAurum && ./install.sh"
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "d" {
            Show-Detection
            Read-Host "Press Enter to continue"
        }
        "h" {
            Show-Help
            Read-Host "Press Enter to continue"
        }
        { $_ -in "q", "Q" } {
            Write-Info "Installation cancelled"
            exit 0
        }
        default {
            Write-Warning "Invalid choice. Please select 1-4, d, h, or q"
            Start-Sleep -Seconds 1
        }
    }
}
