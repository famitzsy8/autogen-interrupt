from __future__ import annotations

import os

from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from handlers.websocket_handler import WebSocketHandler

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Lifespan context manager for application startup/shutdown
    print("Starting agent run...")
    # Logging is configured at module import time in base_group_chat_manager.py
    yield
    print("Shutting down agent run backend...")

app = FastAPI(
    title="Autogen Backend API",
    description="Backend API for any autogen agentchat run",
    version="1.0.0",
    lifespan=lifespan
)

cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
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
        "message": "Deep Research Backend API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket) -> None:
    """WebSocket endpoint for agent team communication."""
    handler = WebSocketHandler(websocket)
    await handler.handle_connection()
