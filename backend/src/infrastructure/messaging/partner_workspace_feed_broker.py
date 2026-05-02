from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PartnerWorkspaceFeedBroadcast:
    workspace_id: UUID
    event_key: str
    event_name: str
    aggregate_type: str
    aggregate_id: str
    subject: str
    payload: dict[str, object]
    occurred_at: datetime


class PartnerWorkspaceFeedBroker:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, list[asyncio.Queue[PartnerWorkspaceFeedBroadcast]]] = {}

    def subscribe(self, workspace_id: UUID) -> asyncio.Queue[PartnerWorkspaceFeedBroadcast]:
        queue: asyncio.Queue[PartnerWorkspaceFeedBroadcast] = asyncio.Queue()
        self._subscribers.setdefault(workspace_id, []).append(queue)
        return queue

    def unsubscribe(self, workspace_id: UUID, queue: asyncio.Queue[PartnerWorkspaceFeedBroadcast]) -> None:
        if workspace_id not in self._subscribers:
            return
        self._subscribers[workspace_id] = [item for item in self._subscribers[workspace_id] if item is not queue]
        if not self._subscribers[workspace_id]:
            del self._subscribers[workspace_id]

    async def publish(self, event: PartnerWorkspaceFeedBroadcast) -> None:
        for queue in self._subscribers.get(event.workspace_id, []):
            await queue.put(event)


partner_workspace_feed_broker = PartnerWorkspaceFeedBroker()
