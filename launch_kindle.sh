#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to the kindleReader script
KINDLE_READER="$SCRIPT_DIR/kindleReader"

# Make sure the path is absolute
if [[ ! "$KINDLE_READER" = /* ]]; then
    KINDLE_READER="$(pwd)/$KINDLE_READER"
fi

# Ensure the AppleScript is in the same directory
APPLESCRIPT_PATH="$SCRIPT_DIR/launch_in_warp.scpt"

# Check if the AppleScript exists
if [ ! -f "$APPLESCRIPT_PATH" ]; then
    echo "Error: AppleScript file not found at $APPLESCRIPT_PATH"
    exit 1
fi

# Check if the kindleReader script exists
if [ ! -f "$KINDLE_READER" ]; then
    echo "Error: kindleReader script not found at $KINDLE_READER"
    exit 1
fi

# Execute the AppleScript with the kindleReader path as argument
osascript "$APPLESCRIPT_PATH" "$KINDLE_READER"

echo "Launched kindleReader in Warp"

