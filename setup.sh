#!/bin/bash

# Meshtastic BBS Server - Installation Script
# Run this script on your Raspberry Pi

set -e

echo "========================================="
echo "Meshtastic BBS Server - Setup"
echo "========================================="

# Check if running on Raspberry Pi
if command -v raspberrypi-config &> /dev/null; then
    echo "Detected Raspberry Pi"
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 not found. Install with: sudo apt install python3"
    exit 1
fi

echo "Python3 version: $(python3 --version)"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if config exists
if [ -f "config.yaml" ]; then
    echo "Config file already exists"
else
    if [ -f "config.example.yaml" ]; then
        echo "Creating config.yaml from example..."
        cp config.example.yaml config.yaml
        echo ""
        echo "IMPORTANT: Edit config.yaml before running!"
        echo "  nano config.yaml"
        echo ""
        echo "Key settings to check:"
        echo "  - bbs.node_id"
        echo "  - serial.devices"
        echo ""
    else
        echo "Error: config.example.yaml not found"
        exit 1
    fi
fi

# Create directories for database and logs
echo "Creating data directories..."
mkdir -p "$(dirname "$(grep 'path:' config.yaml 2>/dev/null | head -1 | cut -d' ' -f2)" 2>/dev/null || echo "/var/lib/meshtastic-bbs")"
mkdir -p "$(dirname "$(grep 'file:' config.yaml 2>/dev/null | head -1 | cut -d' ' -f2)" 2>/dev/null || echo "/var/log/meshtastic-bbs")"

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "To start the BBS server:"
echo "  source venv/bin/activate"
echo "  python -m bbs.Application"
echo ""
echo "Or use the run.sh script:"
echo "  ./run.sh"
