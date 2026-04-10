"""Deterministic load-budget test for the Helix canary evidence route.

Unlike the Locust scenario in ``test_helix_load.py``, this test runs fully
in-process and does not require a booted backend, Redis, or Docker.

This path is intentionally stronger than a stubbed route test:
it exercises ``backend route -> HelixService -> HelixAdapterClient`` and
verifies typed canary evidence parsing under concurrent load.
"""

from __future__ import annotations

import asyncio
import math
import os
import time
import uuid
from statistics import mean
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, MockTransport, Request, Response

os.environ.setdefault("REMNAWAVE_TOKEN", "test-token")
os.environ.setdefault("JWT_SECRET", "0123456789abcdef0123456789abcdefLONG")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.application.services.helix_service import HelixService
from src.domain.enums.enums import AdminRole
from src.infrastructure.helix.client import HelixAdapterClient
from src.presentation.api.v1.helix.routes import router as helix_router
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.helix import get_helix_service


class DummySubscriptionClient:
    """Placeholder dependency for admin-only Helix service paths."""


def _build_canary_payload(rollout_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "rollout_id": rollout_id,
        "channel": "canary",
        "evaluated_at": "2026-04-02T18:00:00Z",
        "decision": "watch",
        "reasons": ["channel posture=watch"],
        "evidence_gaps": ["throughput evidence observations=0"],
        "recommended_follow_up_action": "collect-more-evidence",
        "recommended_follow_up_severity": "warning",
        "recommended_follow_up_tasks": [
            "Run Helix recovery drill and target-matrix benchmarks on the affected desktop cohort.",
            "Capture support bundles until continuity and throughput evidence reach the canary thresholds.",
            "Keep the rollout on watch until evidence gaps are cleared.",
        ],
        "thresholds": {
            "min_connect_success_rate": 0.98,
            "max_fallback_rate": 0.03,
            "min_continuity_observations": 5,
            "require_throughput_evidence": True,
            "min_relative_throughput_ratio": 0.90,
            "max_relative_open_to_first_byte_gap_ratio": 1.15,
            "min_continuity_success_rate": 0.80,
            "min_cross_route_recovery_rate": 0.20,
        },
        "snapshot": {
            "desired_state": "running",
            "failed_nodes": 0,
            "rolled_back_nodes": 0,
            "connect_success_rate": 0.995,
            "fallback_rate": 0.0,
            "continuity_observed_events": 8,
            "continuity_success_rate": 0.96,
            "cross_route_recovery_rate": 0.42,
            "benchmark_observed_events": 6,
            "throughput_evidence_observed_events": 4,
            "average_benchmark_throughput_kbps": 78_124.6,
            "average_relative_throughput_ratio": 1.04,
            "average_relative_open_to_first_byte_gap_ratio": 0.94,
            "channel_posture": "watch",
            "active_profile_advisory_state": "watch",
            "active_profile_new_session_posture": "watch",
            "applied_automatic_reaction": None,
            "applied_transport_profile_id": None,
        },
    }


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    index = max(math.ceil(len(ordered) * 0.95) - 1, 0)
    return ordered[index]


@pytest.mark.asyncio
async def test_helix_canary_evidence_route_under_concurrent_load_meets_internal_budget():
    test_app = FastAPI()
    test_app.include_router(helix_router, prefix="/api/v1")

    operator = SimpleNamespace(
        id=uuid.uuid4(),
        role=AdminRole.OPERATOR,
        is_active=True,
    )
    adapter_calls = 0

    def handler(request: Request) -> Response:
        nonlocal adapter_calls
        adapter_calls += 1
        assert request.headers.get("x-internal-token") == "adapter-token"
        assert request.url.path.startswith("/internal/rollouts/rollout-canary-")
        assert request.url.path.endswith("/canary-evidence")
        rollout_id = request.url.path.split("/")[-2]
        return Response(
            200,
            json=_build_canary_payload(rollout_id),
        )

    adapter_client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=MockTransport(handler),
    )
    service = HelixService(
        adapter_client=adapter_client,
        subscription_client=DummySubscriptionClient(),
    )

    async def _auth_override():
        return operator

    async def _service_override():
        return service

    test_app.dependency_overrides[get_current_active_user] = _auth_override
    test_app.dependency_overrides[get_helix_service] = _service_override

    total_requests = 48
    concurrency = 8
    semaphore = asyncio.Semaphore(concurrency)
    latencies_ms: list[float] = []

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:

        async def _request_once(sequence: int) -> None:
            async with semaphore:
                started_at = time.perf_counter()
                response = await client.get(
                    f"/api/v1/helix/admin/rollouts/rollout-canary-{sequence}/canary-evidence"
                )
                latencies_ms.append((time.perf_counter() - started_at) * 1000)
                assert response.status_code == 200
                payload = response.json()
                assert payload["decision"] == "watch"
                assert payload["recommended_follow_up_action"] == "collect-more-evidence"
                assert payload["snapshot"]["average_relative_throughput_ratio"] == 1.04

        try:
            suite_started_at = time.perf_counter()
            await asyncio.gather(
                *[_request_once(index) for index in range(total_requests)]
            )
            suite_elapsed_ms = (time.perf_counter() - suite_started_at) * 1000
        finally:
            await adapter_client.close()

    assert adapter_calls == total_requests
    assert len(latencies_ms) == total_requests
    assert _p95(latencies_ms) <= 250.0
    assert mean(latencies_ms) <= 150.0
    assert suite_elapsed_ms <= 5000.0
