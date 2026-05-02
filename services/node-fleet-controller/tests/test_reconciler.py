from __future__ import annotations

import os
import tempfile
import unittest

from src.application.services.reconciler import ReconcilerService
from src.application.services.workflow_engine import WorkflowEngine
from src.application.services.audit_service import AuditTrailService
from src.application.services.request_service import FleetRequestService
from src.config import Settings
from src.domain.entities import FleetRequestSubmission
from src.domain.enums import RequestType
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter


class ReconcilerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-reconcile.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)

    async def asyncTearDown(self) -> None:
        await dispose_database(self.settings)

    async def test_run_once_creates_node_and_moves_operation_to_external_step(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            request_service = FleetRequestService(
                repository,
                AuditTrailService(repository),
                NatsJetStreamAdapter(self.settings),
            )
            request, operation = await request_service.submit(
                FleetRequestSubmission(
                    request_type=RequestType.PROVISIONING,
                    requested_by="operator@example.com",
                    idempotency_key="node-add-fr-002",
                    environment="nonprod",
                    country="fr",
                    provider_selector="auto",
                    node_class="standard",
                )
            )
            reconciler = ReconcilerService(repository, WorkflowEngine())

            results = await reconciler.run_once(limit=25)
            nodes = await repository.list_nodes_for_request(request.request_id)
            steps = await repository.list_operation_steps(operation.operation_run_id)
            await session.commit()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].executed_steps, ("select_placement",))
        self.assertTrue(results[0].blocked_on_external_dependency)
        self.assertEqual(results[0].operation_run.current_step, "create_plan")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].country, "fr")
        self.assertEqual(nodes[0].provider, "hetzner")
        self.assertEqual(steps[0].step_name, "select_placement")
