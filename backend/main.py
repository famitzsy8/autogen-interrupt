from __future__ import annotations

import os

from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from websocket_handler import WebSocketHandler

load_dotenv()


# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncIterator[None]:

#     # Lifespan context manager for application startup/shutdown

