#!/bin/bash
# AI Lab - FastAPI Scaffold Runner
# ================================
# Sets up PYTHONPATH and runs the server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Structure: .../ApexAurum/reusable_lib/scaffold/fastapi_app
# We need to add .../ApexAurum to PYTHONPATH (3 levels up)
# so Python can do: from reusable_lib.api import ...
REUSABLE_LIB_PARENT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

# Add to PYTHONPATH
export PYTHONPATH="${REUSABLE_LIB_PARENT}:${PYTHONPATH}"

echo "=== AI Lab FastAPI Server ==="
echo "PYTHONPATH: $PYTHONPATH"
echo "Working dir: $SCRIPT_DIR"
echo ""

# Default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8765}"
RELOAD="${RELOAD:-false}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --reload)
            RELOAD="true"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

cd "$SCRIPT_DIR"

if [ "$RELOAD" = "true" ]; then
    echo "Starting with hot reload on http://${HOST}:${PORT}"
    uvicorn main:app --host "$HOST" --port "$PORT" --reload
else
    echo "Starting on http://${HOST}:${PORT}"
    uvicorn main:app --host "$HOST" --port "$PORT"
fi
