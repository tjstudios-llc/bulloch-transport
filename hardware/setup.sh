#!/bin/bash
# ==============================================================================
# setup.sh - Hardware Kiosk & Transport App Installation Script
# ==============================================================================

set -e # Exit immediately if any command returns a non-zero exit status

# Color formatting for terminal output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}      Starting Transport Kiosk System Setup          ${NC}"
echo -e "${CYAN}====================================================${NC}"

# ------------------------------------------------------------------------------
# 1. CLONE REPOSITORY (Optional / If executed outside repository)
# ------------------------------------------------------------------------------
REPO_URL="https://github.com/tjstudios-llc/bulloch-transport.git" # <-- Update with your repository URL
TARGET_DIR="transport-app"

# Check if script is already inside project root directory or needs to clone
if [ ! -f "hardware/launch_app.sh" ]; then
    if [ ! -d "$TARGET_DIR" ]; then
        echo -e "\n${YELLOW}[1/6] Cloning repository files...${NC}"
        git clone "$REPO_URL" "$TARGET_DIR"
        cd "$TARGET_DIR"
    else
        echo -e "\n${YELLOW}[1/6] Navigating into existing directory '$TARGET_DIR'...${NC}"
        cd "$TARGET_DIR"
    fi
else
    echo -e "\n${YELLOW}[1/6] Already inside project directory.${NC}"
fi

# ------------------------------------------------------------------------------
# 2. UPDATE & INSTALL SYSTEM PACKAGES
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/6] Updating package manager and installing Linux dependencies...${NC}"
sudo apt-get update -y
sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    build-essential

# ------------------------------------------------------------------------------
# 3. PYTHON VIRTUAL ENVIRONMENT & PACKAGE INSTALLATION
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/6] Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}requirements.txt not found. Installing default framework packages...${NC}"
    pip install nicegui firebase-admin requests
fi

# ------------------------------------------------------------------------------
# 4. CONFIGURE SCRIPT PERMISSIONS
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/6] Setting executable permissions for launch scripts...${NC}"
if [ -f "hardware/launch_app.sh" ]; then
    chmod +x hardware/launch_app.sh
    echo -e "${GREEN}chmod +x hardware/launch_app.sh complete.${NC}"
else
    echo -e "${RED}Warning: hardware/launch_app.sh not found!${NC}"
fi

# ------------------------------------------------------------------------------
# 5. REGISTER SYSTEMD KIOSK SERVICE
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/6] Registering transport-kiosk.service with systemd...${NC}"
SERVICE_SRC="hardware/transport-kiosk.service"
SERVICE_DEST="/etc/systemd/system/transport-kiosk.service"

if [ -f "$SERVICE_SRC" ]; then
    sudo cp "$SERVICE_SRC" "$SERVICE_DEST"
    sudo systemctl daemon-reload
    sudo systemctl enable transport-kiosk.service
    echo -e "${GREEN}Service 'transport-kiosk.service' enabled on boot!${NC}"
else
    echo -e "${RED}Warning: $SERVICE_SRC file not found.${NC}"
fi

# ------------------------------------------------------------------------------
# 6. COMPLETION SUMMARY
# ------------------------------------------------------------------------------
echo -e "\n${CYAN}====================================================${NC}"
echo -e "${GREEN}      ✔ Setup completed successfully!              ${NC}"
echo -e "${CYAN}====================================================${NC}"
echo -e "You can control the background kiosk service using:"
echo -e "  Start service:   ${YELLOW}sudo systemctl start transport-kiosk.service${NC}"
echo -e "  Check status:    ${YELLOW}sudo systemctl status transport-kiosk.service${NC}"
echo -e "  View logs:       ${YELLOW}journalctl -u transport-kiosk.service -f${NC}"