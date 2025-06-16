#!/bin/bash

# Sync script for DogTrackerV2 from WSL to K: drive
# Usage: ./sync.sh [watch]
# - Run without arguments for one-time sync
# - Run with 'watch' argument for continuous monitoring

SOURCE_DIR="/home/niko/projects/DogTrackerV2"
DEST_DIR="/mnt/k/DogTrackerV2"
WATCH_MODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if watch mode is requested
if [ "$1" = "watch" ]; then
    WATCH_MODE=true
    echo -e "${BLUE}Starting in WATCH mode - monitoring for changes...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop watching${NC}"
else
    echo -e "${YELLOW}Starting one-time sync from WSL to K: drive...${NC}"
fi

# No external dependencies needed for watch mode

# Function to perform sync
do_sync() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp] Starting sync...${NC}"
    
    # Check if source directory exists
    if [ ! -d "$SOURCE_DIR" ]; then
        echo -e "${RED}Error: Source directory $SOURCE_DIR does not exist${NC}"
        return 1
    fi

    # Check if K: drive is mounted
    if [ ! -d "/mnt/k" ]; then
        echo -e "${RED}Error: K: drive is not mounted at /mnt/k${NC}"
        echo "Try running: sudo mkdir -p /mnt/k && sudo mount -t drvfs K: /mnt/k"
        return 1
    fi

    # Create destination directory if it doesn't exist
    if [ ! -d "$DEST_DIR" ]; then
        echo -e "${YELLOW}Creating destination directory: $DEST_DIR${NC}"
        mkdir -p "$DEST_DIR"
    fi

    # Sync files using rsync with verbose output
    echo -e "${YELLOW}Syncing files (showing changes)...${NC}"
    rsync -avh \
        --progress \
        --delete \
        --itemize-changes \
        --exclude='.git/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='venv/' \
        --exclude='node_modules/' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        "$SOURCE_DIR/" "$DEST_DIR/"

    local sync_result=$?
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ $sync_result -eq 0 ]; then
        echo -e "${GREEN}[$timestamp] Sync completed successfully!${NC}"
        if [ "$WATCH_MODE" = false ]; then
            echo -e "${GREEN}Files synced from: $SOURCE_DIR${NC}"
            echo -e "${GREEN}To: $DEST_DIR${NC}"
            echo -e "${YELLOW}Sync summary:${NC}"
            du -sh "$DEST_DIR"
        fi
    else
        echo -e "${RED}[$timestamp] Sync failed!${NC}"
        return 1
    fi
}

# Handle watch mode vs one-time sync
if [ "$WATCH_MODE" = true ]; then
    # Initial sync
    do_sync
    
    # Watch for changes using simple time-based checking
    echo -e "${BLUE}Watching for changes in $SOURCE_DIR... (checking every 3 seconds)${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop watching${NC}"
    
    # Get initial timestamp
    last_sync=$(date +%s)
    
    while true; do
        sleep 3
        
        # Find files modified in the last 5 seconds
        recent_files=$(find "$SOURCE_DIR" -type f -newermt "@$(($(date +%s) - 5))" 2>/dev/null | grep -v -E '(\.git/|__pycache__/|\.pyc$|venv/|node_modules/|\.log$)' || true)
        
        if [ -n "$recent_files" ]; then
            echo -e "${YELLOW}Changes detected, syncing...${NC}"
            do_sync
            last_sync=$(date +%s)
            echo -e "${BLUE}Continuing to watch for changes...${NC}"
        fi
    done
else
    # One-time sync
    do_sync
fi