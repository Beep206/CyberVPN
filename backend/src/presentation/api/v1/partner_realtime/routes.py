from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.domain.entities.partner_permission import PartnerPermission
from src.infrastructure.database.repositories.partner_event_runtime_repo import PartnerEventRuntimeRepository
from src.infrastructure.messaging.partner_workspace_feed_broker import partner_workspace_feed_broker
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    require_partner_workspace_permission,
)

router = APIRouter(tags=["partners"])


@router.get(
    "/partner-workspaces/{workspace_id}/realtime/feed",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
async def stream_partner_workspace_feed(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    access: PartnerWorkspaceAccess = Depends(require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    repo = PartnerEventRuntimeRepository(db)
    backlog = await repo.list_feed_events(
        workspace_id=access.workspace.id,
        after_event_key=last_event_id,
        limit=settings.partner_realtime_backlog_limit,
    )

    async def event_stream() -> AsyncGenerator[str]:
        queue = partner_workspace_feed_broker.subscribe(access.workspace.id)
        try:
            yield "retry: 5000\n\n"
            for item in backlog:
                yield _format_model_event(item)
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield _format_broker_event(item)
        finally:
            partner_workspace_feed_broker.unsubscribe(access.workspace.id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_model_event(item) -> str:
    data = {
        "aggregate_id": item.aggregate_id,
        "aggregate_type": item.aggregate_type,
        "event_key": item.event_key,
        "event_name": item.event_name,
        "occurred_at": item.occurred_at.isoformat(),
        "payload": dict(item.payload or {}),
        "subject": item.subject,
        "workspace_id": str(item.workspace_id),
    }
    return _encode_sse(data=data, event_key=item.event_key)


def _format_broker_event(item) -> str:
    data = {
        "aggregate_id": item.aggregate_id,
        "aggregate_type": item.aggregate_type,
        "event_key": item.event_key,
        "event_name": item.event_name,
        "occurred_at": item.occurred_at.isoformat(),
        "payload": dict(item.payload or {}),
        "subject": item.subject,
        "workspace_id": str(item.workspace_id),
    }
    return _encode_sse(data=data, event_key=item.event_key)


def _encode_sse(*, data: dict[str, object], event_key: str) -> str:
    return (
        f"id: {event_key}\n"
        "event: partner.workspace.feed\n"
        f"data: {json.dumps(data, separators=(',', ':'))}\n\n"
    )
