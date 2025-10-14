"""FastAPI application for debate backend with WebSocket support."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from websocket_handler import WebSocketHandler

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for application startup/shutdown."""
    # Startup
    print("Starting debate backend...")
    yield
    # Shutdown
    print("Shutting down debate backend...")


# Initialize FastAPI application
app = FastAPI(
    title="Debate Backend API",
    description="Backend API for autogen debate team with WebSocket support",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS middleware for local development
# Allow WebSocket connections from frontend origin
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:8001,http://localhost:8002")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning API information."""
    return {
        "message": "Debate Backend API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/debate")
async def websocket_debate(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for debate team communication.

    Handles real-time streaming of agent messages, user interrupts,
    and user-directed messages with conversation tree branching.

    Protocol:
    - Client sends: UserInterrupt, UserDirectedMessage
    - Server sends: AgentMessage, TreeUpdate, InterruptAcknowledged, StreamEnd, ErrorMessage
    """
    handler = WebSocketHandler(websocket)
    await handler.handle_connection()
