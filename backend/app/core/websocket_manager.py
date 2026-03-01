# @TASK T-WS-1 - WebSocket connection manager for real-time alert push
# @SPEC TRD: "alert delivery within 5 seconds" via WebSocket broadcast
"""
WebSocket connection manager.

Maintains a list of active WebSocket connections and provides a broadcast
method to push messages (e.g. new alerts) to all connected clients.

Thread-safety note:
    The APScheduler alert engine runs in a background thread while
    WebSocket operations are async.  Use ``broadcast_from_thread`` to
    safely schedule the coroutine on the running event loop via
    ``asyncio.run_coroutine_threadsafe``.
"""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket connected (total=%d)", len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket disconnected (total=%d)", len(self.active_connections)
        )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Send a JSON message to every connected client.

        Dead connections are silently removed.
        """
        # Iterate over a copy so removals during iteration are safe.
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                logger.debug("Removing dead WebSocket connection")
                self.active_connections.remove(connection)

    def broadcast_from_thread(self, message: dict[str, Any]) -> None:
        """
        Schedule a broadcast from a non-async context (e.g. APScheduler
        background thread).

        Requires that an asyncio event loop is already running in the
        main thread (which is the case when FastAPI/Uvicorn is serving).
        """
        if not self.active_connections:
            return

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            logger.warning(
                "No event loop available; cannot broadcast WebSocket message"
            )
            return

        if loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
        else:
            logger.warning(
                "Event loop not running; cannot broadcast WebSocket message"
            )


# Singleton instance used across the application.
manager = ConnectionManager()
