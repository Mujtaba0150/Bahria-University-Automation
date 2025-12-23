#!/usr/bin/env bash

set -e

# Resolve script directory (independent of current working directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD=""

# Check if Python already exists
if command -v python3 >/dev/null 2>&1; then
	PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
	PYTHON_CMD="python"
fi

# Install Python only if missing
if [[ -z "$PYTHON_CMD" ]]; then
	echo "Python not found."

	if command -v apt >/dev/null 2>&1; then
		echo "Installing Python via apt..."
		sudo apt update
		sudo apt install -y python3 python3-pip
		PYTHON_CMD="python3"
	elif command -v dnf >/dev/null 2>&1; then
		echo "Installing Python via dnf..."
		sudo dnf install -y python3 python3-pip
		PYTHON_CMD="python3"
	elif command -v pacman >/dev/null 2>&1; then
		echo "Installing Python via pacman..."
		sudo pacman -Sy --noconfirm python python-pip
		PYTHON_CMD="python"
	elif command -v brew >/dev/null 2>&1; then
		echo "Installing Python via Homebrew..."
		brew install python
		PYTHON_CMD="python3"
	else
		echo "No supported package manager found. Install Python manually."
		exit 1
	fi
fi

echo "Using Python command: $PYTHON_CMD"

# Upgrade pip and install requirements
echo "Upgrading pip and installing requirements..."
"$PYTHON_CMD" -m pip install --upgrade pip
"$PYTHON_CMD" -m pip install -r "$SCRIPT_DIR/requirements.txt"

# Collect environment variables from user
read -rp "Enter your ENROLLMENT_NUMBER: " ENROLLMENT_NUMBER
read -rp "Enter your PASSWORD: " PASSWORD
read -rp "Enter your USER_DATA_DIR (absolute path for Playwright profile): " USER_DATA_DIR
read -rp "Enter your DOWNLOAD_DIR (where assignments will be saved): " DOWNLOAD_DIR
read -rp "Enter INSTITUTION selection (default 6): " INSTITUTION
INSTITUTION=${INSTITUTION:-6}
read -rp "Enter DISABLED (0 = No, 1 = Yes): " DISABLED
DISABLED=${DISABLED:-0}
read -rp "Enter GENDER (0 = Male, 1 = Female): " GENDER
GENDER=${GENDER:-0}
read -rp "Enter AGE group (0 = <22, 1 = 22-29, 2 = >29): " AGE
AGE=${AGE:-0}
read -rp "Enter ON_CAMPUS (1 = On campus, 0 = Off campus): " ON_CAMPUS
ON_CAMPUS=${ON_CAMPUS:-1}
echo
echo "NOTIFICATION_LEVEL options:"
echo "  0 = Due Today"
echo "  1 = Up to next 4 days"
echo "  2 = Up to 7 days"
echo "  3 = Up to 14 days"
echo "  4 = All notifications"
read -rp "Enter NOTIFICATION_LEVEL (0-4, default 0): " NOTIFICATION_LEVEL
NOTIFICATION_LEVEL=${NOTIFICATION_LEVEL:-0}
read -rp "Enter NOTIFY_SUBMITTED (0 = No, 1 = Yes, default 1): " NOTIFY_SUBMITTED
NOTIFY_SUBMITTED=${NOTIFY_SUBMITTED:-1}

# Write .env file
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

echo
# Ask if user wants to create command aliases first
read -rp "Do you want to create command aliases for the scripts? (y/n): " CREATE_ALIASES

if [[ "$CREATE_ALIASES" =~ ^[Yy]$ ]]; then
	# Ask user about installation scope
	echo
	echo "Do you want to install scripts for:"
	echo "[1] Current user only"
	echo "[2] All users (requires sudo)"
	read -rp "Enter your choice (1 or 2): " INSTALL_SCOPE

	if [[ "$INSTALL_SCOPE" == "2" ]]; then
		# System-wide aliases and PATH
		echo "Creating system-wide aliases and adding script directory to PATH..."
		SYSTEM_FILE="/etc/profile.d/bahria_automation.sh"
		sudo tee "$SYSTEM_FILE" >/dev/null <<EOF
# Bahria automation aliases
alias checkAssignments="$PYTHON_CMD '$SCRIPT_DIR/checkAssignments.py'"
alias checkAttendance="$PYTHON_CMD '$SCRIPT_DIR/checkAttendance.py'"
alias fillSurveys="$PYTHON_CMD '$SCRIPT_DIR/fillSurveys.py'"

export PATH="\$PATH:$SCRIPT_DIR"
EOF
		sudo chmod +x "$SYSTEM_FILE"
		echo "System-wide aliases and PATH added at $SYSTEM_FILE"
	else
		# User-only aliases and PATH
		echo
		echo "=== Alias setup for user ==="
		echo "Where do you want to install aliases?"
		echo "[1] ~/.bashrc"
		echo "[2] ~/.zshrc"
		echo "[3] ~/.bashrc.d/bash_alias.sh"
		echo "[4] ~/.zshrc.d/zsh_alias.sh"
		echo "[5] Separate .sh file per alias (executable)"
		read -rp "Enter your choice (1-5): " ALIAS_MODE

		read -rp "Enter command alias for checkAssignments.py: " ASSIGNMENTS_ALIAS
		read -rp "Enter command alias for checkAttendance.py: " ATTENDANCE_ALIAS
		read -rp "Enter command alias for fillSurveys.py: " SURVEYS_ALIAS

		writeAlias() {
			local targetFile="$1"

			{
				echo ""
				echo "# Bahria automation aliases"
				echo "alias $ASSIGNMENTS_ALIAS=\"$PYTHON_CMD '$SCRIPT_DIR/checkAssignments.py'\""
				echo "alias $ATTENDANCE_ALIAS=\"$PYTHON_CMD '$SCRIPT_DIR/checkAttendance.py'\""
				echo "alias $SURVEYS_ALIAS=\"$PYTHON_CMD '$SCRIPT_DIR/fillSurveys.py'\""
			} >> "$targetFile"
		}

		case "$ALIAS_MODE" in
			1)
				writeAlias "$HOME/.bashrc"
				PROFILE="$HOME/.bashrc"
				;;
			2)
				writeAlias "$HOME/.zshrc"
				PROFILE="$HOME/.zshrc"
				;;
			3)
				ALIAS_FILE="$HOME/.bashrc.d/bash_alias.sh"
				mkdir -p "$(dirname "$ALIAS_FILE")"
				touch "$ALIAS_FILE"
				writeAlias "$ALIAS_FILE"
				PROFILE="$ALIAS_FILE"
				;;
			4)
				ALIAS_FILE="$HOME/.zshrc.d/zsh_alias.sh"
				mkdir -p "$(dirname "$ALIAS_FILE")"
				touch "$ALIAS_FILE"
				writeAlias "$ALIAS_FILE"
				PROFILE="$ALIAS_FILE"
				;;
			5)
				createAliasScript() {
					local aliasName="$1"
					local scriptName="$2"

					cat > "$SCRIPT_DIR/$aliasName.sh" <<EOF
#!/usr/bin/env bash
"$PYTHON_CMD" "$SCRIPT_DIR/$scriptName" "\$@"
EOF
					chmod +x "$SCRIPT_DIR/$aliasName.sh"
				}

				createAliasScript "$ASSIGNMENTS_ALIAS" "checkAssignments.py"
				createAliasScript "$ATTENDANCE_ALIAS" "checkAttendance.py"
				createAliasScript "$SURVEYS_ALIAS" "fillSurveys.py"
				PROFILE="" # PATH addition not needed for separate scripts
				;;
			*)
				echo "Invalid choice. Skipping alias setup."
				PROFILE=""
				;;
		esac

		# Add script directory to user PATH only if PROFILE is set
		if [[ -n "$PROFILE" ]]; then
			echo "export PATH=\"\$PATH:$SCRIPT_DIR\"" >> "$PROFILE"
			echo "User PATH updated in $PROFILE. Restart your terminal to apply changes."
		fi
	fi
else
	echo
	echo "Skipping alias creation."
fi

echo
echo "Setup complete."
