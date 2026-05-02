from __future__ import annotations

import os
import tempfile
import unittest

from src.application.services.external_node_baseline_service import ExternalNodeBaselineService
from src.config import Settings
from src.domain.entities import NodeRecord
from src.domain.enums import (
    AdapterAckState,
    BootstrapState,
    CertificateState,
    ComponentStatus,
    EnrollmentStatus,
    LifecycleState,
    ProviderResourceState,
    SignalSeverity,
    SyntheticStatus,
    TrafficEligibilityState,
)
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database


class P33BaselineServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p33.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)

    async def asyncTearDown(self) -> None:
        await dispose_database(self.settings)

    async def test_baseline_and_traffic_eligibility_flow(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            await repository.upsert_node(
                NodeRecord(
                    node_id="node_fr_02",
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
            service = ExternalNodeBaselineService(repository)

            profile = await service.get_baseline_profile(node_id="node_fr_02")
            self.assertEqual(profile.runtime_adapter_slug, "helix-adapter")
            self.assertEqual(profile.required_services, ("alloy", "fleet-health-agent", "vpn-daemon"))

            await service.report_observed_state(
                node_id="node_fr_02",
                services_status={
                    "alloy": ComponentStatus.RUNNING.value,
                    "fleet-health-agent": ComponentStatus.RUNNING.value,
                    "vpn-daemon": ComponentStatus.RUNNING.value,
                },
                alloy_telemetry_flowing=True,
                enrollment_hook_completed=True,
            )
            await service.ingest_health_signal(
                node_id="node_fr_02",
                signal_type="heartbeat",
                severity=SignalSeverity.INFO,
                source="fleet-health-agent",
                component="fleet-health-agent",
                details={"latency_ms": 42},
            )
            await service.record_synthetic_check(
                node_id="node_fr_02",
                probe="egress-connectivity",
                status=SyntheticStatus.PASSED,
                source="synthetic-runner",
            )

            ready_evaluation = await service.evaluate_traffic_eligibility(node_id="node_fr_02")
            self.assertEqual(ready_evaluation.eligibility.eligibility_state, TrafficEligibilityState.READY)
            self.assertIn("runtime_adapter_not_acknowledged", ready_evaluation.eligibility.blocked_reasons)

            await service.record_runtime_readiness(
                node_id="node_fr_02",
                adapter_slug="helix-adapter",
                ack_state=AdapterAckState.ACKNOWLEDGED,
                details={"rollout_channel": "stable"},
            )
            eligible_evaluation = await service.evaluate_traffic_eligibility(node_id="node_fr_02")
            await session.commit()

        self.assertEqual(eligible_evaluation.eligibility.eligibility_state, TrafficEligibilityState.ELIGIBLE)
        self.assertEqual(eligible_evaluation.node.current_lifecycle_state, LifecycleState.TRAFFIC_ELIGIBLE)
        self.assertEqual(eligible_evaluation.observed_state.runtime_adapter_ack_state, AdapterAckState.ACKNOWLEDGED)
