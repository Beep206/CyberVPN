import json
import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._channels_by_connection: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default", *, accept: bool = True) -> None:
        if accept and websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)
        self._channels_by_connection.setdefault(websocket, set()).add(channel)

    def disconnect(self, websocket: WebSocket, channel: str = "default") -> None:
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]
        if websocket in self._channels_by_connection:
            self._channels_by_connection[websocket].discard(channel)
            if not self._channels_by_connection[websocket]:
                del self._channels_by_connection[websocket]

    def disconnect_all(self, websocket: WebSocket) -> None:
        for channel in tuple(self._channels_by_connection.get(websocket, ())):
            self.disconnect(websocket, channel)

    async def broadcast(self, channel: str, data: dict[str, Any]) -> None:
        if channel not in self._connections:
            return
        message = json.dumps(data)
        disconnected = set()
        for ws in self._connections[channel]:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning("WebSocket send failed, marking for disconnect: %s", e)
                disconnected.add(ws)
        for ws in disconnected:
            self.disconnect(ws, channel)

    async def send_personal(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(data))

    @property
    def active_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


ws_manager = WebSocketManager()
