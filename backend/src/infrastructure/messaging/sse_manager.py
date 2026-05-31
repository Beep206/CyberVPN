import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any


class SSEManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, channel: str, *, max_queue_size: int = 100) -> asyncio.Queue[dict[str, Any]]:
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers[channel].append(queue)
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if channel in self._subscribers:
            self._subscribers[channel] = [q for q in self._subscribers[channel] if q is not queue]
            if not self._subscribers[channel]:
                del self._subscribers[channel]

    async def broadcast_event(self, channel: str, event: str, data: dict[str, Any]) -> None:
        if channel not in self._subscribers:
            return
        message = {"event": event, "data": data}
        for queue in tuple(self._subscribers[channel]):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                queue.put_nowait(
                    {
                        "event": "sync_required",
                        "data": {"reason": "subscriber_backpressure"},
                    }
                )

    async def create_stream(
        self,
        channel: str,
        *,
        heartbeat_interval_seconds: float = 15.0,
        max_queue_size: int = 100,
    ) -> AsyncGenerator[str]:
        queue = self.subscribe(channel, max_queue_size=max_queue_size)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval_seconds)
                except TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
                    continue
                yield _format_sse_event(str(message["event"]), dict(message["data"]))
        finally:
            self.unsubscribe(channel, queue)


def _format_sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'), default=str)}\n\n"


sse_manager = SSEManager()
