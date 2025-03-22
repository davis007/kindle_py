#!/bin/bash

# ====================================================================
# Enhanced Kindle Reader Launcher Script
# - Launches Kindle Reader in Warp terminal
# - Includes debug output, pauses, and error handling
# ====================================================================

# Enable better error handling
set -E

# Trap any errors
trap 'echo "ERROR: Command failed at line $LINENO with status $?"; read -p "Press Enter to continue..."' ERR

# Debug mode (set to true for verbose output)
DEBUG=true

# Function for debug output
debug_log() {
    if [ "$DEBUG" = true ]; then
        echo "DEBUG: $1"
    fi
}

# Function to handle errors
handle_error() {
    echo "================================================"
    echo "ERROR: $1"
    echo "================================================"
    read -p "Press Enter to exit..."
    exit 1
}

# Pause function
pause() {
    read -p "$1 (Press Enter to continue...)" 
}

# ====================================================================
# SCRIPT START
# ====================================================================

echo "================================================"
echo "KINDLE READER LAUNCHER"
echo "================================================"
pause "Beginning launch process."

# Get the directory where this script is located
debug_log "Determining script directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"

# Path to the kindleReader script
KINDLE_READER="$SCRIPT_DIR/kindleReader"
debug_log "Looking for kindleReader at: $KINDLE_READER"

# Make sure the path is absolute
if [[ ! "$KINDLE_READER" = /* ]]; then
    debug_log "Converting to absolute path..."
    KINDLE_READER="$(pwd)/$KINDLE_READER"
fi
echo "Kindle Reader script path: $KINDLE_READER"

# Check if the kindleReader script exists
if [ ! -f "$KINDLE_READER" ]; then
    handle_error "kindleReader script not found at $KINDLE_READER"
fi
echo "✓ Kindle Reader script found"

# Check if Warp is installed
if ! [ -d "/Applications/Warp.app" ]; then
    handle_error "Warp terminal application not found in /Applications folder"
fi
echo "✓ Warp application found"

# Start Warp directly without using AppleScript
echo "Starting Warp terminal application..."
open -a "Warp" 

# Wait for Warp to start
echo "Waiting for Warp to initialize..."
sleep 2

# Pause to check if Warp is open
pause "Warp should now be open."

# Run the kindleReader script in Warp
echo "Sending command to run Kindle Reader..."
osascript <<EOF
tell application "Warp"
    activate
    delay 1
    tell application "System Events" to keystroke "$KINDLE_READER" & return
end tell
EOF

# Check if the osascript command succeeded
if [ $? -ne 0 ]; then
    handle_error "Failed to send command to Warp. Ensure Warp has necessary permissions."
fi

echo "✓ Command sent to Warp"
echo "================================================"
echo "Kindle Reader should now be running in Warp"
echo "================================================"

# Final pause to verify everything is working
pause "Process complete."
