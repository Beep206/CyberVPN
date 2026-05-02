from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from src.application.services.audit_service import AuditTrailService
from src.application.services.operator_command_service import OperatorCommandService
from src.application.services.request_service import FleetRequestService
from src.config import Settings
from src.domain.entities import NodePoolRecord, NodeRecord
from src.domain.enums import (
    BootstrapState,
    CertificateState,
    EnrollmentStatus,
    LifecycleState,
    ProviderResourceState,
    RequestType,
)
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter
from src.main import create_app


class P34OperatorCommandServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p34.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)

    async def asyncTearDown(self) -> None:
        await dispose_database(self.settings)

    async def test_node_add_and_capacity_adjustment_create_durable_requests(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))
            operator_service = OperatorCommandService(repository, request_service)

            add_result = await operator_service.submit_node_add(
                requested_by="operator@example.com",
                idempotency_key="node-add-jp-standard-001",
                environment="nonprod",
                country="jp",
                role="vpn",
                node_class="standard",
                provider_selector="auto",
                region_selector=None,
                requested_capacity_delta=2,
                approval_mode="automatic",
            )
            scale_result = await operator_service.adjust_pool_capacity(
                node_pool_id=add_result.node_pool.node_pool_id,
                requested_by="operator@example.com",
                idempotency_key="node-pool-scale-jp-standard-001",
                target_desired_capacity=3,
                reason_code="manual_scale_out",
                approval_mode="automatic",
            )
            await session.commit()

        self.assertEqual(add_result.command_name, "node-add")
        self.assertEqual(add_result.node_pool.desired_capacity, 2)
        self.assertEqual(add_result.request.request_type, RequestType.PROVISIONING)
        self.assertEqual(scale_result.node_pool.desired_capacity, 3)
        self.assertEqual(scale_result.request.request_type, RequestType.PROVISIONING)
        self.assertEqual(scale_result.request.requested_capacity_delta, 1)

    async def test_replace_drain_and_quarantine_use_target_node(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            await repository.upsert_node_pool(
                NodePoolRecord(
                    node_pool_id="nonprod-fr-vpn-standard",
                    environment="nonprod",
                    country="fr",
                    role="vpn",
                    node_class="standard",
                    provider_selector="hetzner",
                    region_selector="hel1",
                    desired_capacity=1,
                    current_capacity=1,
                )
            )
            await repository.upsert_node(
                NodeRecord(
                    node_id="node_fr_04",
                    environment="nonprod",
                    role="vpn",
                    country="fr",
                    provider="hetzner",
                    region="hel1",
                    node_class="standard",
                    current_lifecycle_state=LifecycleState.READY,
                    enrollment_status=EnrollmentStatus.ACCEPTED,
                    bootstrap_state=BootstrapState.CONSUMED,
                    certificate_state=CertificateState.ACTIVE,
                    provider_resource_state=ProviderResourceState.ACTIVE,
                )
            )
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))
            operator_service = OperatorCommandService(repository, request_service)

            replace_result = await operator_service.submit_node_replace(
                requested_by="operator@example.com",
                idempotency_key="replace-node-fr-04",
                target_node_id="node_fr_04",
                reason_code="dpi_detected",
                approval_mode="automatic",
            )
            drain_result = await operator_service.submit_node_drain(
                requested_by="operator@example.com",
                idempotency_key="drain-node-fr-04",
                target_node_id="node_fr_04",
                reason_code="planned_rotation",
                approval_mode="automatic",
            )
            quarantine_result = await operator_service.submit_node_quarantine(
                requested_by="operator@example.com",
                idempotency_key="quarantine-node-fr-04",
                target_node_id="node_fr_04",
                reason_code="health_impairment",
                approval_mode="automatic",
            )
            await session.commit()

        self.assertEqual(replace_result.request.request_type, RequestType.REPLACEMENT)
        self.assertEqual(drain_result.request.request_type, RequestType.DRAIN)
        self.assertEqual(quarantine_result.request.request_type, RequestType.QUARANTINE)


class P34OperatorApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p34-api.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            await repository.upsert_node(
                NodeRecord(
                    node_id="node_fr_05",
                    environment="nonprod",
                    role="vpn",
                    country="fr",
                    provider="hetzner",
                    region="hel1",
                    node_class="standard",
                    current_lifecycle_state=LifecycleState.READY,
                    enrollment_status=EnrollmentStatus.ACCEPTED,
                    bootstrap_state=BootstrapState.CONSUMED,
                    certificate_state=CertificateState.ACTIVE,
                    provider_resource_state=ProviderResourceState.ACTIVE,
                )
            )
            await session.commit()
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()

    async def asyncTearDown(self) -> None:
        self.client.__exit__(None, None, None)
        await dispose_database(self.settings)

    async def test_operator_routes_submit_typed_commands(self) -> None:
        add_response = self.client.post(
            "/api/v1/operator/node-add",
            json={
                "requested_by": "operator@example.com",
                "idempotency_key": "node-add-de-standard-001",
                "environment": "nonprod",
                "country": "de",
                "role": "vpn",
                "node_class": "standard",
                "provider_selector": "auto",
                "requested_capacity_delta": 1,
            },
        )
        self.assertEqual(add_response.status_code, 202)
        add_body = add_response.json()
        pool_id = add_body["node_pool"]["node_pool_id"]
        self.assertEqual(add_body["request"]["request_type"], "provisioning")

        capacity_response = self.client.post(
            f"/api/v1/node-pools/{pool_id}/capacity",
            json={
                "requested_by": "operator@example.com",
                "idempotency_key": "capacity-de-standard-002",
                "target_desired_capacity": 2,
                "reason_code": "manual_scale_out",
            },
        )
        self.assertEqual(capacity_response.status_code, 202)
        self.assertEqual(capacity_response.json()["node_pool"]["desired_capacity"], 2)

        replace_response = self.client.post(
            "/api/v1/operator/node-replace",
            json={
                "requested_by": "operator@example.com",
                "idempotency_key": "replace-node-fr-05",
                "target_node_id": "node_fr_05",
                "reason_code": "dpi_detected",
            },
        )
        self.assertEqual(replace_response.status_code, 202)
        self.assertEqual(replace_response.json()["request"]["request_type"], "replacement")

        drain_response = self.client.post(
            "/api/v1/operator/node-drain",
            json={
                "requested_by": "operator@example.com",
                "idempotency_key": "drain-node-fr-05",
                "target_node_id": "node_fr_05",
                "reason_code": "planned_rotation",
            },
        )
        self.assertEqual(drain_response.status_code, 202)
        self.assertEqual(drain_response.json()["request"]["request_type"], "drain")

        quarantine_response = self.client.post(
            "/api/v1/operator/node-quarantine",
            json={
                "requested_by": "operator@example.com",
                "idempotency_key": "quarantine-node-fr-05",
                "target_node_id": "node_fr_05",
                "reason_code": "health_impairment",
            },
        )
        self.assertEqual(quarantine_response.status_code, 202)
        self.assertEqual(quarantine_response.json()["request"]["request_type"], "quarantine")
