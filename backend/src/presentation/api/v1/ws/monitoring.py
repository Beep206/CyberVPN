import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.infrastructure.messaging.websocket_manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/monitoring")
async def monitoring_ws(websocket: WebSocket):
    await ws_manager.connect(websocket, "monitoring")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "subscribe":
                topics = message.get("topics", [])
                for topic in topics:
                    await ws_manager.connect(websocket, f"monitoring:{topic}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "monitoring")
