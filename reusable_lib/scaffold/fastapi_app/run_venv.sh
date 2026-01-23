#!/bin/bash
# FastAPI Lab Edition - with venv
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REUSABLE_LIB_PARENT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
export PYTHONPATH="${REUSABLE_LIB_PARENT}:${PYTHONPATH}"

cd "$SCRIPT_DIR"
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8765 "$@"
