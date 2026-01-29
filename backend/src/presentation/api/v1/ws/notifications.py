import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.infrastructure.messaging.websocket_manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    await ws_manager.connect(websocket, "notifications")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "notifications")
