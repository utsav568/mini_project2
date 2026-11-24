"""
roadsafety/backend/websocket_manager.py
=======================================
High-performance WebSocket connection manager broadcasting real-time
telemetry, GPS updates, and incident transitions across all ecosystem dashboards.
"""

import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("roadsafety.websocket")


class ConnectionManager:
    """Manages active WebSocket connections and topic subscriptions."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Broadcast payload to all connected clients."""
        payload = json.dumps({
            "type": event_type,
            "data": data,
        })
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as exc:
                logger.warning(f"Error broadcasting to client: {exc}")
                disconnected.append(connection)

        for dead_conn in disconnected:
            self.disconnect(dead_conn)


ws_manager = ConnectionManager()
