#!/bin/bash

# Debate Frontend Startup Script
# This script starts the Vite development server for the debate frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Debate Frontend...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}.env file created with default settings${NC}"
    else
        echo -e "${YELLOW}Warning: .env.example not found. Using defaults.${NC}"
    fi
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found. Installing dependencies...${NC}"
    npm install
fi

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
if [ -f .env ]; then
    echo -e "  WebSocket URL: $(grep VITE_WS_URL .env | cut -d '=' -f2 || echo 'ws://localhost:5173/ws/debate')"
else
    echo -e "  WebSocket URL: ws://localhost:5173/ws/debate (default)"
fi

# Start the development server
echo -e "${GREEN}Starting Vite development server on http://localhost:8001${NC}"
echo -e "${YELLOW}Make sure the backend is running on http://localhost:5173${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run Vite dev server
npm run dev
