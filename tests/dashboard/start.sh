#!/bin/bash
# Start Test Dashboard Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if dependencies are installed
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start server
echo ""
echo "========================================"
echo "  Starting Test Dashboard Server..."
echo "========================================"
echo ""
python3 server.py
