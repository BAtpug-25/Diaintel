"""
DiaIntel - WebSocket handler.
Real-time updates via WebSocket connection.
"""

import asyncio
import logging
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("diaintel.websocket")
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected. Active: %s", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected. Active: %s", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_signal_update(self, signal_count: int, last_updated: str):
        await self.broadcast(
            {
                "type": "signal_count",
                "data": {
                    "count": signal_count,
                    "last_updated": last_updated,
                },
            }
        )

    async def send_processing_progress(self, progress: float, message: str, details: Dict[str, Any] | None = None):
        payload = {
            "type": "processing_progress",
            "data": {
                "progress": progress,
                "message": message,
            },
        }
        if details:
            payload["data"].update(details)
        await self.broadcast(payload)


manager = ConnectionManager()


def _schedule(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


def broadcast_signal_update_sync(signal_count: int, last_updated: str):
    try:
        _schedule(manager.send_signal_update(signal_count, last_updated))
    except Exception as exc:
        logger.debug("Signal update broadcast skipped: %s", exc)


def broadcast_processing_progress_sync(progress: float, message: str, details: Dict[str, Any] | None = None):
    try:
        _schedule(manager.send_processing_progress(progress, message, details))
    except Exception as exc:
        logger.debug("Processing progress broadcast skipped: %s", exc)


@router.websocket("/ws/live-updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live DiaIntel ingestion and signal updates."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        manager.disconnect(websocket)
