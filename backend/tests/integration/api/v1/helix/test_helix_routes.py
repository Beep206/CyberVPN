import uuid
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from src.main import app
from src.application.services.helix_service import HelixManifestUnavailableError
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.helix import (
    get_helix_service,
)


@dataclass
class StubHelixService:
    last_runtime_event_command = None

    async def get_capability_defaults_for_user(self, _current_user):
        return {
            "schema_version": "1.1",
            "client_family": "desktop-tauri",
            "default_channel": "lab",
            "supported_protocol_versions": [1],
            "supported_transport_profiles": [
                {
                    "profile_family": "edge-hybrid",
                    "min_transport_profile_version": 1,
                    "max_transport_profile_version": 4,
                    "supported_policy_versions": [4, 5, 6, 7],
                }
            ],
            "required_capabilities": ["protocol.v1"],
            "fallback_cores": ["sing-box", "xray"],
            "rollout_channels": ["lab", "canary", "stable"],
        }

    async def resolve_manifest_for_user(self, current_user, command):
        desktop_client_id = command.desktop_client_id or f"desktop-{current_user.id}"
        return {
            "manifest_version_id": str(uuid.uuid4()),
            "manifest": {
                "schema_version": "1.1",
                "manifest_id": str(uuid.uuid4()),
                "rollout_id": "rollout-lab-1",
                "issued_at": "2026-03-31T09:00:00Z",
                "expires_at": "2026-03-31T10:00:00Z",
                "subject": {
                    "user_id": str(current_user.id),
                    "desktop_client_id": desktop_client_id,
                    "entitlement_id": f"subscription:{current_user.id}",
                    "channel": "lab",
                },
                "transport": {
                    "transport_family": "helix",
                    "protocol_version": 1,
                    "session_mode": "hybrid",
                },
                "transport_profile": {
                    "transport_profile_id": "ptp-lab-edge-v2",
                    "profile_family": "edge-hybrid",
                    "profile_version": 2,
                    "policy_version": 4,
                    "deprecation_state": "active",
                },
                "compatibility_window": {
                    "profile_family": "edge-hybrid",
                    "min_transport_profile_version": 1,
                    "max_transport_profile_version": 4,
                },
                "capability_profile": {
                    "required_capabilities": ["protocol.v1"],
                    "fallback_core": "sing-box",
                    "health_policy": {
                        "startup_timeout_seconds": 15,
                        "runtime_unhealthy_threshold": 3,
                    },
                },
                "routes": [
                    {
                        "endpoint_ref": "pt-lab-node",
                        "preference": 10,
                        "policy_tag": "primary",
                    }
                ],
                "credentials": {"key_id": "sig-key-test", "token": "pt_tok_123"},
                "integrity": {
                    "manifest_hash": "sha256:1234",
                    "signature": {
                        "alg": "ed25519",
                        "key_id": "sig-key-test",
                        "sig": "signed",
                    },
                },
                "observability": {
                    "trace_id": command.trace_id or "trace-1",
                    "metrics_namespace": "helix",
                },
            },
        }

    async def report_runtime_event_for_user(self, _current_user, command):
        self.last_runtime_event_command = command
        return {
            "status": "accepted",
            "rollout_id": command.rollout_id,
            "event_kind": command.event_kind,
        }

    async def get_rollout_canary_evidence(self, rollout_id):
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
                "continuity_observed_events": 2,
                "continuity_success_rate": 1.0,
                "cross_route_recovery_rate": 1.0,
                "benchmark_observed_events": 0,
                "throughput_evidence_observed_events": 0,
                "average_benchmark_throughput_kbps": None,
                "average_relative_throughput_ratio": None,
                "average_relative_open_to_first_byte_gap_ratio": None,
                "channel_posture": "watch",
                "active_profile_advisory_state": "watch",
                "active_profile_new_session_posture": "watch",
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
async def test_helix_capabilities_return_defaults(
    async_client: AsyncClient,
):
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True)

    async def _auth_override():
        return user

    async def _service_override():
        return StubHelixService()

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.get("/api/v1/helix/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["client_family"] == "desktop-tauri"
    assert data["supported_transport_profiles"][0]["profile_family"] == "edge-hybrid"


@pytest.mark.integration
async def test_helix_manifest_resolution_shapes_response(
    async_client: AsyncClient,
):
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True)

    async def _auth_override():
        return user

    async def _service_override():
        return StubHelixService()

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.post(
        "/api/v1/helix/manifest",
        json={
            "desktop_client_id": "desktop-win11-primary",
            "supported_protocol_versions": [1],
            "supported_transport_profiles": [
                {
                    "profile_family": "edge-hybrid",
                    "min_transport_profile_version": 1,
                    "max_transport_profile_version": 4,
                    "supported_policy_versions": [4, 5, 6, 7],
                }
            ],
            "preferred_fallback_core": "sing-box",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["manifest"]["subject"]["desktop_client_id"] == "desktop-win11-primary"
    assert (
        data["manifest"]["transport_profile"]["transport_profile_id"]
        == "ptp-lab-edge-v2"
    )


@pytest.mark.integration
async def test_helix_runtime_event_is_forwarded_through_backend(
    async_client: AsyncClient,
):
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
    stub_service = StubHelixService()

    async def _auth_override():
        return user

    async def _service_override():
        return stub_service

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.post(
        "/api/v1/helix/events/runtime",
        json={
            "desktop_client_id": "desktop-win11-primary",
            "manifest_version_id": str(uuid.uuid4()),
            "rollout_id": "rollout-lab-1",
            "transport_profile_id": "ptp-lab-edge-v2",
            "event_kind": "ready",
            "active_core": "helix",
            "latency_ms": 142,
            "route_count": 2,
            "payload": {
                "runtime": "embedded-sidecar",
                "status": "ready",
                "recovery": {
                    "same_route_recovered": True,
                    "ready_recovery_latency_ms": 37,
                    "proxy_ready_latency_ms": 49,
                },
                "continuity": {
                    "active_streams": 3,
                    "continuity_grace_active": True,
                    "continuity_grace_entries": 2,
                    "successful_continuity_recovers": 1,
                },
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["event_kind"] == "ready"
    assert stub_service.last_runtime_event_command is not None
    assert stub_service.last_runtime_event_command.payload is not None
    assert (
        stub_service.last_runtime_event_command.payload.recovery.ready_recovery_latency_ms
        == 37
    )
    assert (
        stub_service.last_runtime_event_command.payload.continuity
        .successful_continuity_recovers
        == 1
    )


@pytest.mark.integration
async def test_helix_runtime_benchmark_event_is_forwarded_through_backend(
    async_client: AsyncClient,
):
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
    stub_service = StubHelixService()

    async def _auth_override():
        return user

    async def _service_override():
        return stub_service

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.post(
        "/api/v1/helix/events/runtime",
        json={
            "desktop_client_id": "desktop-win11-primary",
            "manifest_version_id": str(uuid.uuid4()),
            "rollout_id": "rollout-lab-1",
            "transport_profile_id": "ptp-lab-edge-v2",
            "event_kind": "benchmark",
            "active_core": "helix",
            "route_count": 2,
            "payload": {
                "benchmark_kind": "comparison",
                "baseline_core": "sing-box",
                "target_count": 3,
                "successful_targets": 3,
                "attempts": 3,
                "successes": 3,
                "failures": 0,
                "throughput_kbps": 81234.5,
                "relative_throughput_ratio_vs_baseline": 1.18,
                "median_connect_latency_ms": 12,
                "median_first_byte_latency_ms": 84,
                "median_open_to_first_byte_gap_ms": 72,
                "p95_open_to_first_byte_gap_ms": 95,
                "relative_open_to_first_byte_gap_ratio_vs_baseline": 0.91,
                "frame_queue_peak": 8,
                "recent_rtt_p95_ms": 41,
                "active_streams": 4,
                "pending_open_streams": 1,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["event_kind"] == "benchmark"
    assert stub_service.last_runtime_event_command is not None
    assert stub_service.last_runtime_event_command.event_kind == "benchmark"
    assert stub_service.last_runtime_event_command.payload is not None
    assert stub_service.last_runtime_event_command.payload.benchmark is not None
    assert (
        stub_service.last_runtime_event_command.payload.benchmark.baseline_core
        == "sing-box"
    )
    assert (
        stub_service.last_runtime_event_command.payload.benchmark
        .relative_throughput_ratio_vs_baseline
        == 1.18
    )
    assert (
        stub_service.last_runtime_event_command.payload.benchmark
        .median_open_to_first_byte_gap_ms
        == 72
    )


@pytest.mark.integration
async def test_helix_rollout_canary_evidence_is_exposed_through_admin_api(
    async_client: AsyncClient,
):
    operator = SimpleNamespace(id=uuid.uuid4(), role="operator", is_active=True)

    async def _auth_override():
        return operator

    async def _service_override():
        return StubHelixService()

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.get(
        "/api/v1/helix/admin/rollouts/rollout-canary-1/canary-evidence"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "watch"
    assert data["channel"] == "canary"
    assert data["thresholds"]["require_throughput_evidence"] is True
    assert data["snapshot"]["channel_posture"] == "watch"
    assert data["evidence_gaps"] == ["throughput evidence observations=0"]
    assert data["recommended_follow_up_action"] == "collect-more-evidence"


@pytest.mark.integration
async def test_helix_manifest_returns_hidden_not_found_when_manifest_is_unavailable(
    async_client: AsyncClient,
):
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True)

    async def _auth_override():
        return user

    class RefusingHelixService:
        async def resolve_manifest_for_user(self, *_args, **_kwargs):
            raise HelixManifestUnavailableError("no eligible Helix profile")

    async def _service_override():
        return RefusingHelixService()

    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_helix_service] = _service_override

    response = await async_client.post(
        "/api/v1/helix/manifest",
        json={
            "desktop_client_id": "desktop-win11-primary",
            "supported_protocol_versions": [1],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"
