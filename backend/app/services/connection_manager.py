from fastapi import WebSocket
from typing import Optional

from app.utils.logger import logger


class ConnectionManager:
    """Manages WebSocket connections and their conversation state"""
    def __init__(self):
        self.active_connections: dict[WebSocket, Optional[int]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = None
        logger.info("WebSocket connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        logger.info("WebSocket disconnected")


manager = ConnectionManager()
