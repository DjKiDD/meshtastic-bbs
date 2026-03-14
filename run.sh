#!/bin/bash

# Meshtastic BBS Server - Run Script
# Run this to start the BBS server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run setup.sh first!"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "Config file not found. Run setup.sh first!"
    exit 1
fi

# Run the BBS
python -m bbs.Application "$@"
