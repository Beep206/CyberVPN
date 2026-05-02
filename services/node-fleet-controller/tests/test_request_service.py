from __future__ import annotations

import asyncio
import os
import tempfile
import unittest

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import AuditTrailService
from src.application.services.request_service import FleetRequestService
from src.config import Settings
from src.domain.entities import FleetRequestSubmission
from src.domain.enums import RequestType
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter


class RequestServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)

    async def asyncTearDown(self) -> None:
        await dispose_database(self.settings)

    async def test_submit_creates_request_operation_and_audit_entries(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            service = FleetRequestService(
                FleetRequestRepository(session),
                AuditTrailService(FleetRequestRepository(session)),
                NatsJetStreamAdapter(self.settings),
            )
            request, operation = await service.submit(
                FleetRequestSubmission(
                    request_type=RequestType.PROVISIONING,
                    requested_by="operator@example.com",
                    idempotency_key="node-add-jp-001",
                    environment="nonprod",
                    country="jp",
                    provider_selector="auto",
                    node_class="standard",
                    requested_capacity_delta=1,
                )
            )
            await session.commit()

        async with session_factory() as verification_session:
            repository = FleetRequestRepository(verification_session)
            stored_request = await repository.get_request(request.request_id)
            audit_entries = await repository.list_audit_entries(request_id=request.request_id)

        self.assertIsNotNone(stored_request)
        self.assertEqual(stored_request.request_type, RequestType.PROVISIONING)
        self.assertEqual(operation.current_step, "request_accepted")
        self.assertEqual(len(audit_entries), 2)
        self.assertEqual(audit_entries[0].event_type, "fleet.request.accepted")
        self.assertEqual(audit_entries[1].payload["published"], False)

    async def test_submit_is_idempotent_for_same_key(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            service = FleetRequestService(
                FleetRequestRepository(session),
                AuditTrailService(FleetRequestRepository(session)),
                NatsJetStreamAdapter(self.settings),
            )
            first_request, first_operation = await service.submit(
                FleetRequestSubmission(
                    request_type=RequestType.QUARANTINE,
                    requested_by="operator@example.com",
                    idempotency_key="node-quarantine-jp-001",
                    environment="nonprod",
                    target_node_id="node_jp_01",
                    reason_code="health_impairment",
                )
            )
            second_request, second_operation = await service.submit(
                FleetRequestSubmission(
                    request_type=RequestType.QUARANTINE,
                    requested_by="operator@example.com",
                    idempotency_key="node-quarantine-jp-001",
                    environment="nonprod",
                    target_node_id="node_jp_01",
                    reason_code="health_impairment",
                )
            )

        self.assertEqual(first_request.request_id, second_request.request_id)
        self.assertEqual(first_operation.operation_run_id, second_operation.operation_run_id)

