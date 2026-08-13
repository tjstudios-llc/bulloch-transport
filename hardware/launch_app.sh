#!/bin/bash
# hardware/launch_app.sh

# Navigate to the project root directory
cd "$(dirname "$0")/.."

# Activate Python virtual environment if applicable
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set display variable if running a local browser kiosk on X11
export DISPLAY=:0

# Run the device setup app
python3 main.py