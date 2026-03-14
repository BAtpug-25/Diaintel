"""
DiaIntel — WebSocket Handler
Real-time updates via WebSocket connection.
"""

import json
import logging
import asyncio
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("diaintel.websocket")
router = APIRouter()

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_signal_update(self, signal_count: int, last_updated: str):
        """Broadcast new signal count and timestamp."""
        await self.broadcast({
            "type": "signal_count",
            "data": {
                "count": signal_count,
                "last_updated": last_updated,
            }
        })

    async def send_processing_progress(self, progress: float, message: str):
        """Broadcast processing progress during ingestion."""
        await self.broadcast({
            "type": "processing_progress",
            "data": {
                "progress": progress,
                "message": message,
            }
        })


# Singleton manager
manager = ConnectionManager()


@router.websocket("/ws/live-updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live updates.

    Pushes:
    - new signal count
    - last updated timestamp
    - processing progress during ingestion
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            # Echo back or handle client commands
            logger.debug(f"WebSocket received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
