"""Authoritative, idempotent reconciliation for durable Remnawave stream gaps."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_stream_gaps import (
    RemnawaveStreamGapResult,
    RemnawaveStreamGapService,
    RemnawaveStreamGapTransitionError,
)
from src.application.services.remnawave_stream_ingestion import (
    ConnectionUser,
    RemnawaveStreamIngestionService,
)


@dataclass(frozen=True, slots=True)
class AuthoritativeNodePresenceSnapshot:
    node_id: int
    observed_at: datetime
    users: tuple[ConnectionUser, ...]


class RemnawaveStreamAuthoritativeReader(Protocol):
    async def read_user_usage_inventory(self) -> int: ...

    async def read_node_presence_snapshots(self) -> tuple[AuthoritativeNodePresenceSnapshot, ...]: ...


class RemnawaveStreamGapReconciliationService:
    """Refresh recoverable current state and truthfully retain historical loss as partial."""

    def __init__(self, session: AsyncSession, *, reader: RemnawaveStreamAuthoritativeReader) -> None:
        self._session = session
        self._reader = reader

    async def execute(self, gap_id: uuid.UUID) -> RemnawaveStreamGapResult:
        gaps = RemnawaveStreamGapService(self._session)
        current = await gaps.get(gap_id)
        if current.reconciliation_status in {"reconciled", "partial"}:
            return current
        if current.reconciliation_status == "failed":
            raise RemnawaveStreamGapTransitionError("Failed gap reconciliation requires operator review")

        await gaps.transition(
            gap_id=gap_id,
            reconciliation_status="running",
            redacted_detail="rest_reconciliation_started",
            authoritative_read_completed=False,
        )
        # Persist the claim before external I/O. A crash leaves a retryable
        # running row instead of falsely presenting terminal reconciliation.
        await self._session.commit()

        if current.stream_name == "user_usage":
            await self._reader.read_user_usage_inventory()
            terminal_detail = "authoritative_usage_inventory_partial"
        elif current.stream_name == "node_connections":
            snapshots = await self._reader.read_node_presence_snapshots()
            ingestion = RemnawaveStreamIngestionService(self._session)
            for snapshot in snapshots:
                await ingestion.reconcile_current_node_presence(
                    node_id=snapshot.node_id,
                    observed_at=snapshot.observed_at,
                    users=snapshot.users,
                )
            terminal_detail = "authoritative_presence_snapshot_partial"
        else:
            # Subscription request metadata is intentionally never recreated;
            # registration already marks this stream partial.
            terminal_detail = "metadata_not_reconstructable"

        result = await gaps.transition(
            gap_id=gap_id,
            reconciliation_status="partial",
            redacted_detail=terminal_detail,
            authoritative_read_completed=True,
        )
        await self._session.commit()
        return result
