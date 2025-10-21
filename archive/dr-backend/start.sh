#!/bin/bash

# Deep Research Backend Startup Script
# This script starts the FastAPI deep research backend server with uvicorn

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Deep Research Backend...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file and add your OPENAI_API_KEY${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo -e "${RED}Error: OPENAI_API_KEY not set in .env file${NC}"
    echo -e "${YELLOW}Please edit .env and add your OpenAI API key${NC}"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Start the server
echo -e "${GREEN}Starting FastAPI server on http://localhost:8001${NC}"
echo -e "${GREEN}WebSocket endpoint: ws://localhost:8001/ws/research${NC}"
echo -e "${GREEN}API docs available at: http://localhost:8001/docs${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run uvicorn with auto-reload for development
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
