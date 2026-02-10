import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any


class SSEManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, channel: str) -> asyncio.Queue:
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[channel].append(queue)
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        if channel in self._subscribers:
            self._subscribers[channel] = [q for q in self._subscribers[channel] if q is not queue]
            if not self._subscribers[channel]:
                del self._subscribers[channel]

    async def broadcast_event(self, channel: str, event: str, data: dict[str, Any]) -> None:
        if channel not in self._subscribers:
            return
        message = {"event": event, "data": data}
        for queue in self._subscribers[channel]:
            await queue.put(message)

    async def create_stream(self, channel: str) -> AsyncGenerator[str]:
        queue = self.subscribe(channel)
        try:
            while True:
                message = await queue.get()
                yield f"event: {message['event']}\ndata: {json.dumps(message['data'])}\n\n"
        finally:
            self.unsubscribe(channel, queue)


sse_manager = SSEManager()
