#!/bin/bash

# Move all agent_run_state_session_*.json files to trash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERN="agent_run_state_session_*.json"

# Find matching files
files=("$SCRIPT_DIR"/$PATTERN)

# Check if any files match
if [[ ! -e "${files[0]}" ]]; then
    echo "No agent_run_state_session_*.json files found"
    exit 0
fi

count=${#files[@]}
echo "Found $count session file(s) to move to trash"

# Move files to trash using macOS trash command
for file in "${files[@]}"; do
    if osascript -e "tell application \"Finder\" to delete POSIX file \"$file\"" > /dev/null 2>&1; then
        echo "Trashed: $(basename "$file")"
    else
        echo "Failed to trash: $(basename "$file")"
    fi
done

echo "Done! Moved $count file(s) to trash"
