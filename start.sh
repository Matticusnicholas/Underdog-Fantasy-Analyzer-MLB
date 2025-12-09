#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Fantasy Analyzer - MLB Best Ball                  ║${NC}"
echo -e "${CYAN}║              Starting Web Application...                  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 is not installed.${NC}"
    echo "Please install Python 3.9+ from https://python.org"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[OK] Python $PYTHON_VERSION found${NC}"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[INFO] Creating virtual environment...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Failed to create virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK] Virtual environment created.${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}[INFO] Activating virtual environment...${NC}"
source venv/bin/activate

# Check if requirements are installed
if ! python -c "import flask" &> /dev/null; then
    echo -e "${BLUE}[INFO] Installing requirements...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Failed to install requirements.${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK] Requirements installed.${NC}"
else
    echo -e "${GREEN}[OK] Requirements already installed.${NC}"
fi

# Install package in development mode if not already
if ! python -c "import analyzer" &> /dev/null; then
    echo -e "${BLUE}[INFO] Installing package...${NC}"
    pip install -e . > /dev/null 2>&1
    echo -e "${GREEN}[OK] Package installed.${NC}"
fi

# Create data directories if they don't exist
mkdir -p data/screenshots data/exports

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Starting server at http://localhost:5000                 ║${NC}"
echo -e "${CYAN}║  Press Ctrl+C to stop the server                          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Start the web application
python run_web.py

# Deactivate on exit
deactivate
