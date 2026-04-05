#!/usr/bin/env bash

set -e
set -o pipefail

# ==================================================
# Resolve script directory
# ==================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    echo "No Python with pip found. Installing..."

    if command -v apt >/dev/null 2>&1; then
        sudo apt update
        sudo apt install -y python3 python3-pip
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm python python-pip
    elif command -v brew >/dev/null 2>&1; then
        brew install python
    else
        echo "Unsupported package manager. Install Python manually."
        exit 1
    fi

    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"

# ==================================================
# Install dependencies
# ==================================================
echo "Upgrading pip and installing requirements..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"
$PYTHON_CMD -m playwright install chromium

clear

# ==================================================
# Collect environment variables
# ==================================================
read -p "Enter your ENROLLMENT_NUMBER: " ENROLLMENT_NUMBER
read -p "Enter your PASSWORD: " PASSWORD

read -p "Enter USER_DATA_DIR (default ~/.local/share/ms-playwright): " USER_DATA_DIR
USER_DATA_DIR=${USER_DATA_DIR:-"$HOME/.local/share/ms-playwright"}

read -p "Enter DOWNLOAD_DIR (default ~/Documents/Assignments): " DOWNLOAD_DIR
DOWNLOAD_DIR=${DOWNLOAD_DIR:-"$HOME/Documents/Assignments"}

read -p "Enter INSTITUTION (default 6): " INSTITUTION
INSTITUTION=${INSTITUTION:-6}

read -p "Enter DISABLED (0/1, default 0): " DISABLED
DISABLED=${DISABLED:-0}

read -p "Enter GENDER (0=Male,1=Female, default 0): " GENDER
GENDER=${GENDER:-0}

read -p "Enter AGE (0=<22,1=22-29,2=>29, default 0): " AGE
AGE=${AGE:-0}

read -p "Enter ON_CAMPUS (1/0, default 1): " ON_CAMPUS
ON_CAMPUS=${ON_CAMPUS:-1}

echo ""
echo "NOTIFICATION_LEVEL:"
echo "  0 = Due Today"
echo "  1 = Next 4 days"
echo "  2 = 7 days"
echo "  3 = 14 days"
echo "  4 = All"

read -p "Enter (0-4, default 0): " NOTIFICATION_LEVEL
NOTIFICATION_LEVEL=${NOTIFICATION_LEVEL:-0}

read -p "Notify submitted? (0/1, default 1): " NOTIFY_SUBMITTED
NOTIFY_SUBMITTED=${NOTIFY_SUBMITTED:-1}

# ==================================================
# Write .env file
# ==================================================
echo "Writing .env file..."

cat > "$SCRIPT_DIR/.env" <<EOF
ENROLLMENT_NUMBER=$ENROLLMENT_NUMBER
PASSWORD=$PASSWORD
USER_DATA_DIR=$USER_DATA_DIR
DOWNLOAD_DIR=$DOWNLOAD_DIR
INSTITUTION=$INSTITUTION
DISABLED=$DISABLED
GENDER=$GENDER
AGE=$AGE
ON_CAMPUS=$ON_CAMPUS
NOTIFICATION_LEVEL=$NOTIFICATION_LEVEL
NOTIFY_SUBMITTED=$NOTIFY_SUBMITTED
EOF

clear

# ==================================================
# Alias creation
# ==================================================
read -p "Create command aliases? (y/n): " CREATE_ALIASES

if [[ "$CREATE_ALIASES" == "y" ]]; then
    read -p "Alias for checkAssignments.py: " ASSIGNMENTS_ALIAS
    read -p "Alias for checkAttendance.py: " ATTENDANCE_ALIAS
    read -p "Alias for fillSurveys.py: " SURVEYS_ALIAS

    # Detect Shell and Target File
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        TARGET_RC="$HOME/.zshrc"
    elif [[ -f "$HOME/.bash_aliases" ]]; then
        TARGET_RC="$HOME/.bash_aliases"
    else
        TARGET_RC="$HOME/.bashrc"
    fi

    echo "Adding aliases to $TARGET_RC..."

    # Append to config file
    cat >> "$TARGET_RC" <<EOF

# --- Automation Script Aliases ---
alias $ASSIGNMENTS_ALIAS='$PYTHON_CMD "$SCRIPT_DIR/checkAssignments.py"'
alias $ATTENDANCE_ALIAS='$PYTHON_CMD "$SCRIPT_DIR/checkAttendance.py"'
alias $SURVEYS_ALIAS='$PYTHON_CMD "$SCRIPT_DIR/fillSurveys.py"'
EOF

    echo "Aliases added successfully."
    echo "Run 'source $TARGET_RC' to start using them."
fi

# ==================================================
# Done
# ==================================================
echo ""
echo "Setup complete. You can now use your aliases in the terminal."