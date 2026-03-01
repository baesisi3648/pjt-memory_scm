# @TASK T-WS-2 - WebSocket endpoint for real-time alert notifications
# @SPEC TRD: "alert delivery within 5 seconds" via WebSocket push
"""
WebSocket endpoint for real-time alert notifications.

Clients connect to ``ws://host/api/v1/ws`` to receive push messages
whenever new alerts are created by the alert engine.

Authentication is not required for WebSocket connections (simplified
for the current phase).
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, func, select

from app.core.database import engine
from app.core.websocket_manager import manager
from app.models.alert import Alert

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_unread_alert_count() -> int:
    """Return the number of unread alerts (sync, lightweight query)."""
    with Session(engine) as session:
        statement = select(func.count()).select_from(Alert).where(
            Alert.is_read == False  # noqa: E712
        )
        count = session.exec(statement).one()
        return count


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time notifications.

    On connect:
        - Accepts the connection and sends a welcome message with
          the current unread alert count.

    While connected:
        - Keeps the connection alive by reading incoming messages
          (pings/heartbeats from the client).
        - Server pushes alert notifications via ``ConnectionManager.broadcast``.

    On disconnect:
        - Cleans up the connection from the manager.
    """
    await manager.connect(websocket)

    try:
        # Send welcome message with current unread count.
        unread_count = _get_unread_alert_count()
        await websocket.send_json({
            "type": "welcome",
            "unread_count": unread_count,
        })

        # Keep connection alive -- wait for client messages (pings/close).
        while True:
            # receive_text blocks until the client sends something or
            # the connection closes, keeping the coroutine alive.
            data = await websocket.receive_text()
            # Client can send "ping" to keep alive; respond with "pong".
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        logger.exception("WebSocket error")
        manager.disconnect(websocket)
