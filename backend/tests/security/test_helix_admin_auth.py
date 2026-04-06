import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from src.main import app
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.helix import get_helix_service


class StubHelixAdminService:
    async def list_nodes(self):
        return []

    async def get_rollout_canary_evidence(self, _rollout_id: str):
        return {
            "schema_version": "1.0",
            "rollout_id": "rollout-canary-1",
            "channel": "canary",
            "evaluated_at": "2026-04-02T18:00:00Z",
            "decision": "watch",
            "reasons": [],
            "evidence_gaps": [],
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
                "connect_success_rate": 1.0,
                "fallback_rate": 0.0,
                "continuity_observed_events": 0,
                "continuity_success_rate": 0.0,
                "cross_route_recovery_rate": 0.0,
                "benchmark_observed_events": 0,
                "throughput_evidence_observed_events": 0,
                "average_benchmark_throughput_kbps": None,
                "average_relative_throughput_ratio": None,
                "average_relative_open_to_first_byte_gap_ratio": None,
                "channel_posture": "healthy",
                "active_profile_advisory_state": None,
                "active_profile_new_session_posture": None,
                "applied_automatic_reaction": None,
                "applied_transport_profile_id": None,
            },
        }


@pytest.fixture(autouse=True)
def _clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.integration
async def test_helix_admin_nodes_requires_auth(async_client: AsyncClient):
    async def _service_override():
        return StubHelixAdminService()

    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.get("/api/v1/helix/admin/nodes")
    assert response.status_code == 401


@pytest.mark.integration
async def test_helix_admin_nodes_rejects_viewer_role(
    async_client: AsyncClient,
):
    viewer = SimpleNamespace(id=uuid.uuid4(), role="viewer", is_active=True)

    async def _auth_override():
        return viewer

    async def _service_override():
        return StubHelixAdminService()

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.get("/api/v1/helix/admin/nodes")

    assert response.status_code == 403


@pytest.mark.integration
async def test_helix_admin_canary_evidence_requires_auth(async_client: AsyncClient):
    async def _service_override():
        return StubHelixAdminService()

    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.get(
        "/api/v1/helix/admin/rollouts/rollout-canary-1/canary-evidence"
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_helix_admin_canary_evidence_rejects_viewer_role(
    async_client: AsyncClient,
):
    viewer = SimpleNamespace(id=uuid.uuid4(), role="viewer", is_active=True)

    async def _auth_override():
        return viewer

    async def _service_override():
        return StubHelixAdminService()

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.get(
        "/api/v1/helix/admin/rollouts/rollout-canary-1/canary-evidence"
    )

    assert response.status_code == 403
