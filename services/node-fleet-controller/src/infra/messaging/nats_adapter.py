from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.config import Settings
from src.domain.entities import FleetRequestRecord, OperationRunRecord
from src.domain.enums import RequestType

COMMAND_SUBJECTS: dict[RequestType, str] = {
    RequestType.PROVISIONING: "node.command.provision_requested.v1",
    RequestType.REPLACEMENT: "node.command.replace_requested.v1",
    RequestType.DRAIN: "node.command.drain_requested.v1",
    RequestType.QUARANTINE: "node.command.quarantine_requested.v1",
    RequestType.FAILOVER: "node.command.failover_requested.v1",
}


@dataclass(frozen=True)
class PublishedEventPreview:
    subject: str
    envelope: dict[str, Any]
    published: bool


class NatsJetStreamAdapter:
    """Thin adapter for canonical request publication to JetStream."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: Any | None = None
        self._jetstream: Any | None = None

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.drain()
            self._connection = None
            self._jetstream = None

    async def publish_request_accepted(
        self,
        *,
        request: FleetRequestRecord,
        operation_run: OperationRunRecord,
    ) -> PublishedEventPreview:
        subject = COMMAND_SUBJECTS[request.request_type]
        envelope = self.build_request_envelope(
            request=request,
            operation_run=operation_run,
            subject=subject,
        )
        if not self._settings.nats_publish_enabled:
            return PublishedEventPreview(subject=subject, envelope=envelope, published=False)

        await self._ensure_connection()
        payload = json.dumps(envelope, default=str, separators=(",", ":")).encode("utf-8")
        await self._jetstream.publish(subject, payload)
        return PublishedEventPreview(subject=subject, envelope=envelope, published=True)

    def build_request_envelope(
        self,
        *,
        request: FleetRequestRecord,
        operation_run: OperationRunRecord,
        subject: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        event_type = subject.removesuffix(".v1")
        return {
            "event_id": f"evt_{uuid.uuid4().hex}",
            "event_type": event_type,
            "event_version": 1,
            "subject": subject,
            "source": self._settings.nats_source,
            "occurred_at": request.created_at.isoformat(),
            "published_at": now,
            "environment": request.environment,
            "aggregate_type": "fleet_request",
            "aggregate_id": request.request_id,
            "correlation_id": request.correlation_id or request.request_id,
            "idempotency_key": request.idempotency_key,
            "pii_classification": "low",
            "schema_ref": f"events/{event_type.replace('.', '/')}/v1.json",
            "payload": {
                "request_id": request.request_id,
                "request_type": request.request_type.value,
                "operation_run_id": operation_run.operation_run_id,
                "requested_by": request.requested_by,
                "requested_capacity_delta": request.requested_capacity_delta,
                "country": request.country,
                "provider_selector": request.provider_selector,
                "region_selector": request.region_selector,
                "node_class": request.node_class,
                "node_pool_id": request.node_pool_id,
                "target_node_id": request.target_node_id,
                "reason_code": request.reason_code,
                "approval_mode": request.approval_mode,
            },
        }

    async def _ensure_connection(self) -> None:
        if self._connection is not None:
            return
        import nats

        self._connection = await nats.connect(self._settings.nats_url, name=self._settings.service_name)
        self._jetstream = self._connection.jetstream()

