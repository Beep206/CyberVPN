from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.infrastructure.messaging.nats_partner_runtime import (
    NatsPartnerRuntime,
    OutboxEnvelope,
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


@pytest.mark.asyncio
async def test_publish_envelope_uses_stream_and_nats_msg_id() -> None:
    class FakeAck:
        stream = "PARTNER_EVENTS"
        seq = 42
        duplicate = False

    class FakeJetStream:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def publish(self, subject, payload, **kwargs):
            self.calls.append({"subject": subject, "payload": payload, **kwargs})
            return FakeAck()

    runtime = NatsPartnerRuntime()
    fake_jetstream = FakeJetStream()
    runtime._jetstream = fake_jetstream
    envelope = OutboxEnvelope(
        consumer_key="analytics_mart",
        event_key="evt_test_001",
        event_name="entitlement.grant.activated",
        event_family="entitlement",
        aggregate_type="entitlement_grant",
        aggregate_id="grant-001",
        schema_version=1,
        subject="partner.analytics_mart.entitlement.grant.activated.v1",
        occurred_at=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
        actor_context={},
        source_context={},
        event_payload={"customer_account_id": "customer-001"},
    )

    ack = await runtime._publish_envelope(envelope)

    assert fake_jetstream.calls[0]["subject"] == envelope.subject
    assert fake_jetstream.calls[0]["stream"] == "PARTNER_EVENTS"
    assert fake_jetstream.calls[0]["headers"] == {"Nats-Msg-Id": "analytics_mart:evt_test_001"}
    assert ack["broker_sequence"] == 42
    assert ack["idempotency_key"] == "analytics_mart:evt_test_001"
    assert ack["event_version"] == 1
