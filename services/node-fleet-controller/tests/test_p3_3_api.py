from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from src.config import Settings
from src.domain.entities import NodeRecord
from src.domain.enums import (
    BootstrapState,
    CertificateState,
    EnrollmentStatus,
    LifecycleState,
    ProviderResourceState,
)
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database
from src.main import create_app


class P33ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p33-api.sqlite3")
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
                    node_id="node_fr_03",
                    environment="nonprod",
                    role="vpn",
                    country="fr",
                    provider="hetzner",
                    region="hel1",
                    node_class="standard",
                    current_lifecycle_state=LifecycleState.CONFIGURING,
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

    async def test_baseline_and_eligibility_routes(self) -> None:
        baseline_response = self.client.get("/api/v1/nodes/node_fr_03/baseline")
        self.assertEqual(baseline_response.status_code, 200)
        self.assertEqual(baseline_response.json()["runtime_adapter_slug"], "helix-adapter")

        observed_response = self.client.post(
            "/api/v1/nodes/node_fr_03/observed-state",
            json={
                "services_status": {
                    "alloy": "running",
                    "fleet-health-agent": "running",
                    "vpn-daemon": "running",
                },
                "alloy_telemetry_flowing": True,
                "enrollment_hook_completed": True,
            },
        )
        self.assertEqual(observed_response.status_code, 200)

        health_response = self.client.post(
            "/api/v1/nodes/node_fr_03/health-signals",
            json={
                "signal_type": "heartbeat",
                "severity": "info",
                "source": "fleet-health-agent",
                "component": "fleet-health-agent",
                "details": {"latency_ms": 21},
            },
        )
        self.assertEqual(health_response.status_code, 200)

        synthetic_response = self.client.post(
            "/api/v1/nodes/node_fr_03/synthetic-checks",
            json={
                "probe": "egress-connectivity",
                "status": "passed",
                "source": "synthetic-runner",
                "details": {"egress_ip": "198.51.100.10"},
            },
        )
        self.assertEqual(synthetic_response.status_code, 200)

        runtime_response = self.client.post(
            "/api/v1/nodes/node_fr_03/runtime-readiness",
            json={
                "adapter_slug": "helix-adapter",
                "ack_state": "acknowledged",
                "details": {"profile": "default"},
            },
        )
        self.assertEqual(runtime_response.status_code, 200)

        evaluation_response = self.client.post("/api/v1/nodes/node_fr_03/traffic-eligibility/evaluate")
        self.assertEqual(evaluation_response.status_code, 200)
        body = evaluation_response.json()
        self.assertEqual(body["eligibility"]["eligibility_state"], "eligible")
        self.assertEqual(body["node"]["current_lifecycle_state"], "traffic_eligible")
