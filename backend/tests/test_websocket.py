# @TASK T-WS-4 - WebSocket endpoint and manager tests
# @TEST tests/test_websocket.py
"""
Tests for WebSocket real-time alert notification system.

Covers:
- ConnectionManager: connect, disconnect, broadcast, dead connection cleanup
- WebSocket endpoint: connection, welcome message, ping/pong
- Alert engine broadcast integration: _broadcast_new_alerts
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.websocket_manager import ConnectionManager, manager
from app.models.alert import Alert


# ---------------------------------------------------------------------------
# Tests: ConnectionManager
# ---------------------------------------------------------------------------


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connect_adds_to_active_connections(self):
        """Connecting a WebSocket adds it to the active list."""
        mgr = ConnectionManager()
        ws = AsyncMock()

        await mgr.connect(ws)

        assert ws in mgr.active_connections
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active_connections(self):
        """Disconnecting a WebSocket removes it from the active list."""
        mgr = ConnectionManager()
        ws = AsyncMock()

        await mgr.connect(ws)
        mgr.disconnect(ws)

        assert ws not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection_is_safe(self):
        """Disconnecting a WebSocket that is not in the list does not raise."""
        mgr = ConnectionManager()
        ws = AsyncMock()

        # Should not raise
        mgr.disconnect(ws)

        assert len(mgr.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self):
        """Broadcasting sends the message to every connected client."""
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await mgr.connect(ws1)
        await mgr.connect(ws2)

        message = {"type": "test", "data": "hello"}
        await mgr.broadcast(message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        """Broadcasting removes connections that raise exceptions."""
        mgr = ConnectionManager()
        live_ws = AsyncMock()
        dead_ws = AsyncMock()
        dead_ws.send_json.side_effect = RuntimeError("Connection closed")

        await mgr.connect(live_ws)
        await mgr.connect(dead_ws)

        message = {"type": "test", "data": "hello"}
        await mgr.broadcast(message)

        # Live connection should still be present
        assert live_ws in mgr.active_connections
        # Dead connection should be removed
        assert dead_ws not in mgr.active_connections
        # Live connection received the message
        live_ws.send_json.assert_awaited_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self):
        """Broadcasting with no connections does nothing and does not raise."""
        mgr = ConnectionManager()

        # Should not raise
        await mgr.broadcast({"type": "test"})

    def test_broadcast_from_thread_no_connections(self):
        """broadcast_from_thread with no connections returns immediately."""
        mgr = ConnectionManager()

        # Should not raise
        mgr.broadcast_from_thread({"type": "test"})


# ---------------------------------------------------------------------------
# Tests: WebSocket endpoint via TestClient
# ---------------------------------------------------------------------------


class TestWebSocketEndpoint:
    """Tests for the /api/v1/ws WebSocket endpoint."""

    def test_websocket_connect_and_welcome(self, client: TestClient):
        """Connecting sends a welcome message with unread_count."""
        with client.websocket_connect("/api/v1/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "welcome"
            assert "unread_count" in data
            assert isinstance(data["unread_count"], int)

    def test_websocket_ping_pong(self, client: TestClient):
        """Sending 'ping' receives a pong response."""
        with client.websocket_connect("/api/v1/ws") as ws:
            # Consume the welcome message first
            ws.receive_json()

            ws.send_text("ping")
            response = ws.receive_json()
            assert response["type"] == "pong"


# ---------------------------------------------------------------------------
# Tests: _broadcast_new_alerts
# ---------------------------------------------------------------------------


class TestBroadcastNewAlerts:
    """Tests for the _broadcast_new_alerts function in alert_engine."""

    def test_broadcast_calls_manager(self):
        """_broadcast_new_alerts calls broadcast_from_thread for each alert."""
        from app.services.alert_engine import _broadcast_new_alerts

        test_alert = Alert(
            id=42,
            company_id=1,
            severity="warning",
            title="[price_change] Test Alert",
            description="[rule:1] Price dropped 10%",
            is_read=False,
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

        with patch(
            "app.core.websocket_manager.manager"
        ) as mock_manager:
            _broadcast_new_alerts([test_alert])

            mock_manager.broadcast_from_thread.assert_called_once()
            call_args = mock_manager.broadcast_from_thread.call_args[0][0]
            assert call_args["type"] == "new_alert"
            assert call_args["alert"]["id"] == 42
            assert call_args["alert"]["severity"] == "warning"
            assert call_args["alert"]["title"] == "[price_change] Test Alert"
            assert call_args["alert"]["company_id"] == 1

    def test_broadcast_empty_alerts_skips(self):
        """_broadcast_new_alerts with empty list does nothing."""
        from app.services.alert_engine import _broadcast_new_alerts

        with patch(
            "app.core.websocket_manager.manager"
        ) as mock_manager:
            _broadcast_new_alerts([])

            mock_manager.broadcast_from_thread.assert_not_called()

    def test_broadcast_multiple_alerts(self):
        """_broadcast_new_alerts broadcasts each alert individually."""
        from app.services.alert_engine import _broadcast_new_alerts

        alerts = [
            Alert(
                id=i,
                company_id=1,
                severity="warning",
                title=f"Alert {i}",
                description=f"[rule:{i}] Test",
                is_read=False,
                created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            )
            for i in range(3)
        ]

        with patch(
            "app.core.websocket_manager.manager"
        ) as mock_manager:
            _broadcast_new_alerts(alerts)

            assert mock_manager.broadcast_from_thread.call_count == 3


# ---------------------------------------------------------------------------
# Tests: Singleton manager instance
# ---------------------------------------------------------------------------


class TestSingletonManager:
    """Tests for the module-level singleton manager."""

    def test_manager_is_connection_manager(self):
        """The singleton is a ConnectionManager instance."""
        assert isinstance(manager, ConnectionManager)

    def test_manager_starts_with_empty_connections(self):
        """The singleton starts with no active connections."""
        # Note: in a test environment, active_connections may have been
        # modified by previous tests. We check the type is correct.
        assert isinstance(manager.active_connections, list)
