from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.infrastructure.messaging.nats_partner_runtime import (
    NatsPartnerRuntime,
    _build_subject,
    _extract_workspace_id,
    _parse_datetime,
)


def test_build_subject_uses_consumer_and_version() -> None:
    subject = _build_subject(
        consumer_key="operational_replay",
        event_name="invite.redeemed",
        schema_version=3,
    )

    assert subject == "partner.operational_replay.invite.redeemed.v3"


def test_extract_workspace_id_prefers_payload_and_source_context() -> None:
    workspace_id = uuid4()

    assert (
        _extract_workspace_id(
            {
                "payload": {"partner_account_id": str(workspace_id)},
                "source_context": {},
            }
        )
        == workspace_id
    )
    assert (
        _extract_workspace_id(
            {
                "payload": {},
                "source_context": {"workspace_id": str(workspace_id)},
            }
        )
        == workspace_id
    )


def test_parse_datetime_normalizes_zulu_timestamp() -> None:
    parsed = _parse_datetime("2026-04-23T12:34:56Z")

    assert parsed == datetime(2026, 4, 23, 12, 34, 56, tzinfo=UTC)


@pytest.mark.asyncio
async def test_runtime_start_is_noop_when_backbone_disabled() -> None:
    runtime = NatsPartnerRuntime()

    await runtime.start()

    assert runtime._tasks == []
