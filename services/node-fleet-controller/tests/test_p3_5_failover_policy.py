from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from src.application.services.audit_service import AuditTrailService
from src.application.services.failover_policy_service import FailoverPolicyService
from src.application.services.request_service import FleetRequestService
from src.config import Settings
from src.domain.enums import RequestStatus, RequestType
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter
from src.main import create_app


class P35FailoverPolicyServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p35.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)

    async def asyncTearDown(self) -> None:
        await dispose_database(self.settings)

    async def test_failover_policy_bundle_persists_and_reads_back(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))
            service = FailoverPolicyService(repository, request_service, audit_service)

            await service.upsert_policy_bundle(
                scope_id="nonprod-jp-auto",
                environment="nonprod",
                country="jp",
                provider_selector="auto",
                monthly_limit=10,
                burst_limit=2,
                current_month_spend=0,
                max_actions_per_window=3,
                window_seconds=3600,
                cooldown_seconds=300,
                max_parallel_failovers=2,
                risk_threshold=0.8,
                budget_approval_threshold=2,
                approval_mode="automatic",
                require_human_above_threshold=True,
                confidence_score_threshold=0.7,
                minimum_independent_signal_sources=2,
                country_emergency_stop=False,
                node_class_allowlist=("standard", "high-memory"),
                provider_exclusion_window_seconds=0,
                traffic_canary_required=True,
                rollback_and_drain_policy="parallel_replace_then_drain",
            )
            await session.commit()

        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))
            service = FailoverPolicyService(repository, request_service, audit_service)
            bundle = await service.get_policy_bundle("nonprod-jp-auto")

        self.assertEqual(bundle.scope_id, "nonprod-jp-auto")
        self.assertEqual(bundle.budget_policy.monthly_limit, 10)
        self.assertEqual(bundle.rate_limit_policy.cooldown_seconds, 300)
        self.assertEqual(bundle.approval_policy.risk_threshold, 0.8)
        self.assertEqual(bundle.guardrail_policy.node_class_allowlist, ("standard", "high-memory"))

    async def test_failover_is_blocked_when_confidence_and_signal_thresholds_fail(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))
            service = FailoverPolicyService(repository, request_service, audit_service)
            await service.upsert_policy_bundle(
                scope_id="nonprod-fr-auto",
                environment="nonprod",
                country="fr",
                provider_selector="auto",
                monthly_limit=20,
                burst_limit=5,
                current_month_spend=0,
                max_actions_per_window=3,
                window_seconds=3600,
                cooldown_seconds=0,
                max_parallel_failovers=2,
                risk_threshold=0.9,
                budget_approval_threshold=4,
                approval_mode="automatic",
                require_human_above_threshold=True,
                confidence_score_threshold=0.8,
                minimum_independent_signal_sources=3,
                country_emergency_stop=False,
                node_class_allowlist=("standard",),
                provider_exclusion_window_seconds=0,
                traffic_canary_required=True,
                rollback_and_drain_policy="parallel_replace_then_drain",
            )
            result = await service.submit_failover(
                requested_by="operator@example.com",
                idempotency_key="failover-fr-001",
                environment="nonprod",
                country="fr",
                node_class="standard",
                provider_selector="auto",
                region_selector=None,
                requested_capacity_delta=1,
                approval_mode="automatic",
                signal_group_id="incident-fr-001",
                confidence_score=0.5,
                independent_signal_sources=1,
                budget_impact=1,
                risk_score=0.2,
                reason_code="dpi_detected",
                node_pool_id=None,
                target_node_id="node_fr_01",
            )
            await session.commit()

        self.assertEqual(result.request.request_type, RequestType.FAILOVER)
        self.assertEqual(result.request.status, RequestStatus.BLOCKED_POLICY)
        self.assertIn("confidence_below_threshold", result.policy_evaluation.blocked_reasons)
        self.assertIn("insufficient_signal_sources", result.policy_evaluation.blocked_reasons)

    async def test_failover_requires_approval_or_is_blocked_by_cooldown(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))
            service = FailoverPolicyService(repository, request_service, audit_service)
            await service.upsert_policy_bundle(
                scope_id="nonprod-de-auto",
                environment="nonprod",
                country="de",
                provider_selector="auto",
                monthly_limit=20,
                burst_limit=3,
                current_month_spend=0,
                max_actions_per_window=3,
                window_seconds=3600,
                cooldown_seconds=0,
                max_parallel_failovers=2,
                risk_threshold=0.7,
                budget_approval_threshold=2,
                approval_mode="automatic",
                require_human_above_threshold=True,
                confidence_score_threshold=0.4,
                minimum_independent_signal_sources=1,
                country_emergency_stop=False,
                node_class_allowlist=("standard",),
                provider_exclusion_window_seconds=0,
                traffic_canary_required=True,
                rollback_and_drain_policy="parallel_replace_then_drain",
            )
            approval_result = await service.submit_failover(
                requested_by="operator@example.com",
                idempotency_key="failover-de-approval-001",
                environment="nonprod",
                country="de",
                node_class="standard",
                provider_selector="auto",
                region_selector=None,
                requested_capacity_delta=1,
                approval_mode="automatic",
                signal_group_id="incident-de-approval-001",
                confidence_score=0.95,
                independent_signal_sources=3,
                budget_impact=1,
                risk_score=0.9,
                reason_code="provider_impairment",
                node_pool_id=None,
                target_node_id="node_de_01",
            )
            await service.upsert_policy_bundle(
                scope_id="nonprod-it-auto",
                environment="nonprod",
                country="it",
                provider_selector="auto",
                monthly_limit=20,
                burst_limit=3,
                current_month_spend=0,
                max_actions_per_window=3,
                window_seconds=3600,
                cooldown_seconds=3600,
                max_parallel_failovers=2,
                risk_threshold=0.9,
                budget_approval_threshold=4,
                approval_mode="automatic",
                require_human_above_threshold=True,
                confidence_score_threshold=0.4,
                minimum_independent_signal_sources=1,
                country_emergency_stop=False,
                node_class_allowlist=("standard",),
                provider_exclusion_window_seconds=0,
                traffic_canary_required=True,
                rollback_and_drain_policy="parallel_replace_then_drain",
            )
            accepted_result = await service.submit_failover(
                requested_by="operator@example.com",
                idempotency_key="failover-it-accepted-002",
                environment="nonprod",
                country="it",
                node_class="standard",
                provider_selector="auto",
                region_selector=None,
                requested_capacity_delta=1,
                approval_mode="automatic",
                signal_group_id="incident-it-accepted-002",
                confidence_score=0.95,
                independent_signal_sources=3,
                budget_impact=1,
                risk_score=0.2,
                reason_code="provider_impairment",
                node_pool_id=None,
                target_node_id="node_it_02",
            )
            blocked_result = await service.submit_failover(
                requested_by="operator@example.com",
                idempotency_key="failover-it-cooldown-003",
                environment="nonprod",
                country="it",
                node_class="standard",
                provider_selector="auto",
                region_selector=None,
                requested_capacity_delta=1,
                approval_mode="automatic",
                signal_group_id="incident-it-cooldown-003",
                confidence_score=0.95,
                independent_signal_sources=3,
                budget_impact=1,
                risk_score=0.2,
                reason_code="provider_impairment",
                node_pool_id=None,
                target_node_id="node_it_03",
            )
            await session.commit()

        self.assertEqual(approval_result.request.status, RequestStatus.AWAITING_APPROVAL)
        self.assertTrue(approval_result.policy_evaluation.requires_human_approval)
        self.assertEqual(accepted_result.request.status, RequestStatus.ACCEPTED)
        self.assertEqual(blocked_result.request.status, RequestStatus.BLOCKED_POLICY)
        self.assertIn("cooldown_active", blocked_result.policy_evaluation.blocked_reasons)


class P35FailoverPolicyApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p35-api.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()

    async def asyncTearDown(self) -> None:
        self.client.__exit__(None, None, None)
        await dispose_database(self.settings)

    async def test_policy_routes_and_failover_command_surface(self) -> None:
        put_response = self.client.put(
            "/api/v1/failover-policies/nonprod-es-auto",
            json={
                "environment": "nonprod",
                "country": "es",
                "provider_selector": "auto",
                "budget_policy": {
                    "monthly_limit": 20,
                    "burst_limit": 4,
                    "current_month_spend": 0,
                },
                "rate_limit_policy": {
                    "max_actions_per_window": 3,
                    "window_seconds": 3600,
                    "cooldown_seconds": 0,
                    "max_parallel_failovers": 2,
                },
                "approval_policy": {
                    "risk_threshold": 0.75,
                    "budget_approval_threshold": 3,
                    "approval_mode": "automatic",
                    "require_human_above_threshold": True,
                },
                "guardrail_policy": {
                    "confidence_score_threshold": 0.6,
                    "minimum_independent_signal_sources": 2,
                    "country_emergency_stop": False,
                    "node_class_allowlist": ["standard"],
                    "provider_exclusion_window_seconds": 0,
                    "traffic_canary_required": True,
                    "rollback_and_drain_policy": "parallel_replace_then_drain",
                },
            },
        )
        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json()["scope_id"], "nonprod-es-auto")

        get_response = self.client.get("/api/v1/failover-policies/nonprod-es-auto")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["budget_policy"]["monthly_limit"], 20)

        failover_response = self.client.post(
            "/api/v1/operator/node-failover",
            json={
                "requested_by": "operator@example.com",
                "idempotency_key": "failover-es-001",
                "environment": "nonprod",
                "country": "es",
                "node_class": "standard",
                "provider_selector": "auto",
                "requested_capacity_delta": 1,
                "signal_group_id": "incident-es-001",
                "confidence_score": 0.95,
                "independent_signal_sources": 3,
                "budget_impact": 1,
                "risk_score": 0.2,
                "reason_code": "dpi_detected",
                "target_node_id": "node_es_01",
            },
        )
        self.assertEqual(failover_response.status_code, 202)
        body = failover_response.json()
        self.assertEqual(body["request"]["request_type"], "failover")
        self.assertEqual(body["request"]["status"], "accepted")
        self.assertEqual(body["request"]["signal_group_id"], "incident-es-001")
        self.assertEqual(body["policy_evaluation"]["decision_status"], "accepted")
