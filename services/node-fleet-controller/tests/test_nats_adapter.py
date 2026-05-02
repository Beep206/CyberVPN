from __future__ import annotations

import unittest

from src.config import Settings
from src.domain.entities import FleetRequestRecord, OperationRunRecord
from src.domain.enums import OperationStatus, RequestStatus, RequestType
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter


class NatsAdapterTests(unittest.TestCase):
    def test_build_request_envelope_uses_canonical_subject_and_payload(self) -> None:
        adapter = NatsJetStreamAdapter(Settings(nats_publish_enabled=False, environment="nonprod"))
        request = FleetRequestRecord(
            request_id="req_123",
            request_type=RequestType.PROVISIONING,
            requested_by="operator@example.com",
            idempotency_key="node-add-jp-001",
            status=RequestStatus.ACCEPTED,
            environment="nonprod",
            country="jp",
            provider_selector="auto",
            node_class="standard",
            requested_capacity_delta=1,
        )
        operation = OperationRunRecord(
            operation_run_id="opr_123",
            request_id="req_123",
            operation_name="provisioning_workflow",
            status=OperationStatus.PENDING,
        )

        envelope = adapter.build_request_envelope(
            request=request,
            operation_run=operation,
            subject="node.command.provision_requested.v1",
        )

        self.assertEqual(envelope["event_type"], "node.command.provision_requested")
        self.assertEqual(envelope["subject"], "node.command.provision_requested.v1")
        self.assertEqual(envelope["aggregate_id"], "req_123")
        self.assertEqual(envelope["payload"]["operation_run_id"], "opr_123")

