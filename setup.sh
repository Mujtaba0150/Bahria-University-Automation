#!/usr/bin/env bash

set -e
set -o pipefail

# ==================================================
# Resolve script directory
# ==================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ==================================================
# Colors for output
# ==================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================================================
# Find Python with pip
# ==================================================
PYTHON_CMD=""

if command -v python3 >/dev/null 2>&1 && python3 -m pip --version >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1 && python -m pip --version >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

# Install Python if missing
if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "${YELLOW}No Python with pip found. Installing...${NC}"

    if command -v apt >/dev/null 2>&1; then
        echo "Detected Debian/Ubuntu system"
        sudo apt update
        sudo apt install -y python3 python3-pip python3-tk
    elif command -v dnf >/dev/null 2>&1; then
        echo "Detected Fedora/RHEL system"
        sudo dnf install -y python3 python3-pip python3-tkinter
    elif command -v pacman >/dev/null 2>&1; then
        echo "Detected Arch system"
        sudo pacman -Sy --noconfirm python python-pip tk
    elif command -v brew >/dev/null 2>&1; then
        echo "Detected macOS system"
        brew install python
    else
        echo -e "${RED}Unsupported package manager. Please install Python manually.${NC}"
        echo "You need: Python 3.8+, pip, and tkinter"
        exit 1
    fi

    PYTHON_CMD="python3"
fi

echo -e "${GREEN}Using Python: $PYTHON_CMD${NC}"

# ==================================================
# Verify Python version
# ==================================================
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $PYTHON_VERSION"

# ==================================================
# Install dependencies
# ==================================================
echo -e "${YELLOW}Upgrading pip and installing requirements...${NC}"
$PYTHON_CMD -m pip install --upgrade pip setuptools wheel
$PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"

# Install Playwright browsers
echo -e "${YELLOW}Installing Playwright browsers...${NC}"
$PYTHON_CMD -m playwright install chromium

# ==================================================
# Run setup GUI
# ==================================================
echo -e "${GREEN}Launching setup wizard...${NC}"
cd "$SCRIPT_DIR"
$PYTHON_CMD setup_gui.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo "Your .env file has been created."
    echo ""
    echo "You can now run the scripts:"
    echo "  $PYTHON_CMD checkAssignments.py"
    echo "  $PYTHON_CMD checkAttendance.py"
    echo "  $PYTHON_CMD fillSurveys.py"
else
    echo -e "${RED}Setup wizard was cancelled or encountered an error.${NC}"
    exit 1
fi
