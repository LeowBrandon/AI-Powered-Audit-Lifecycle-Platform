"""Real-time WebSocket connection manager for live monitoring and audit status broadcasts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class MonitoringWebSocketManager:
    """Tracks connected WebSocket clients and broadcasts live governance events."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._recent_events: list[dict[str, Any]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    @property
    def recent_events(self) -> list[dict[str, Any]]:
        return list(self._recent_events[-25:])

    async def connect(self, websocket: WebSocket) -> None:
        self._loop = asyncio.get_running_loop()
        await websocket.accept()
        self._connections.add(websocket)
        await websocket.send_json(
            {
                "event": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_clients": self.active_connections,
                "recent_events": self.recent_events[-10:],
            }
        )

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        message = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        self._recent_events.append(message)
        if len(self._recent_events) > 60:
            self._recent_events = self._recent_events[-60:]

        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    def broadcast_sync(self, event_type: str, payload: dict[str, Any]) -> None:
        """Thread-safe broadcast callable from synchronous FastAPI worker routes."""
        try:
            running = asyncio.get_running_loop()
            running.create_task(self.broadcast(event_type, payload))
            return
        except RuntimeError:
            pass

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(event_type, payload), self._loop)
            return

        self._recent_events.append(
            {
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }
        )


ws_manager = MonitoringWebSocketManager()
