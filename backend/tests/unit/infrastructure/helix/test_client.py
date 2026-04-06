import httpx
import pytest

from src.infrastructure.helix.client import (
    AdapterDesktopRuntimeEventPayload,
    AdapterDesktopRuntimeEventRequest,
    AdapterDesktopRuntimeEventRecoveryEvidence,
    AdapterDesktopRuntimeEventContinuityEvidence,
    AdapterResolveManifestRequest,
    HelixAdapterManifestUnavailableError,
    HelixAdapterClient,
)


@pytest.mark.asyncio
async def test_resolve_manifest_sends_internal_token_and_parses_response():
    observed_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed_headers["x-internal-token"] = request.headers.get("x-internal-token")
        assert request.url.path == "/internal/manifests/resolve"
        return httpx.Response(
            200,
            json={
                "manifest_version_id": "de33fcba-b71d-4f5f-82d2-34ae78977e31",
                "selected_profile_policy": {
                    "observed_events": 6,
                    "connect_success_rate": 0.83,
                    "fallback_rate": 0.17,
                    "continuity_success_rate": 0.8,
                    "cross_route_recovery_rate": 0.67,
                    "policy_score": 784,
                    "degraded": False,
                    "advisory_state": "healthy",
                    "selection_eligible": True,
                    "new_session_issuable": True,
                    "new_session_posture": "preferred",
                },
                "manifest": {
                    "schema_version": "1.1",
                    "manifest_id": "2b00dce8-5a2b-416c-90df-7eacfece0280",
                    "rollout_id": "rollout-lab-1",
                    "issued_at": "2026-03-31T09:00:00Z",
                    "expires_at": "2026-03-31T10:00:00Z",
                    "subject": {
                        "user_id": "user-1",
                        "desktop_client_id": "desktop-1",
                        "entitlement_id": "subscription:user-1",
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
                        "trace_id": "trace-1",
                        "metrics_namespace": "helix",
                    },
                },
            },
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.resolve_manifest(
        AdapterResolveManifestRequest(
            user_id="user-1",
            desktop_client_id="desktop-1",
            entitlement_id="subscription:user-1",
            trace_id="trace-1",
            channel="lab",
            supported_protocol_versions=[1],
        )
    )

    assert observed_headers["x-internal-token"] == "adapter-token"
    assert response.selected_profile_policy is not None
    assert response.selected_profile_policy.policy_score == 784
    assert response.manifest.transport_profile.transport_profile_id == "ptp-lab-edge-v2"
    await client.close()


@pytest.mark.asyncio
async def test_get_capability_defaults_parses_supported_transport_profiles():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
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
            },
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.get_client_capability_defaults()
    assert response.supported_transport_profiles[0].profile_family == "edge-hybrid"
    await client.close()


@pytest.mark.asyncio
async def test_list_transport_profiles_parses_policy_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/admin/transport-profiles"
        return httpx.Response(
            200,
            json=[
                {
                    "transport_profile_id": "ptp-lab-edge-v2",
                    "channel": "lab",
                    "profile_family": "edge-hybrid",
                    "profile_version": 2,
                    "policy_version": 4,
                    "protocol_version": 1,
                    "session_mode": "hybrid",
                    "status": "active",
                    "fallback_core": "sing-box",
                    "required_capabilities": ["protocol.v1"],
                    "compatibility_min_profile_version": 1,
                    "compatibility_max_profile_version": 3,
                    "startup_timeout_seconds": 20,
                    "runtime_unhealthy_threshold": 3,
                    "policy": {
                        "observed_events": 5,
                        "connect_success_rate": 0.8,
                        "fallback_rate": 0.2,
                        "continuity_success_rate": 0.75,
                        "cross_route_recovery_rate": 0.6,
                        "policy_score": 742,
                        "degraded": False,
                        "advisory_state": "watch",
                        "recommended_action": "Continue observing this profile.",
                        "selection_eligible": True,
                        "new_session_issuable": True,
                        "new_session_posture": "watch",
                    },
                    "created_at": "2026-03-31T10:00:00Z",
                    "updated_at": "2026-03-31T10:00:00Z",
                }
            ],
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.list_transport_profiles()
    assert response[0].policy is not None
    assert response[0].policy.policy_score == 742
    assert response[0].policy.degraded is False
    assert response[0].policy.advisory_state == "watch"
    await client.close()


@pytest.mark.asyncio
async def test_get_rollout_status_parses_policy_recommendations():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/rollouts/rollout-lab-1/status"
        return httpx.Response(
            200,
            json={
                "schema_version": "1.0",
                "rollout_id": "rollout-lab-1",
                "channel": "lab",
                "desired_state": "running",
                "published_at": "2026-03-31T10:00:00Z",
                "current_batch": {
                    "batch_id": "batch-1",
                    "manifest_version": "manifest-v1",
                    "target_nodes": 2,
                    "completed_nodes": 1,
                    "failed_nodes": 1,
                },
                "nodes": {"healthy": 1, "stale": 0, "rolled_back": 0},
                "desktop": {
                    "connect_success_rate": 0.7,
                    "fallback_rate": 0.3,
                    "continuity_observed_events": 5,
                    "continuity_success_rate": 0.4,
                    "cross_route_recovery_rate": 0.1,
                    "benchmark_observed_events": 4,
                    "throughput_evidence_observed_events": 3,
                    "average_benchmark_throughput_kbps": 72500.25,
                    "average_relative_throughput_ratio": 1.14,
                    "average_relative_open_to_first_byte_gap_ratio": 0.93,
                },
                "policy": {
                    "pause_on_rollback_spike": True,
                    "revoke_on_manifest_error": True,
                    "active_transport_profile_id": "ptp-lab-edge-v7",
                    "active_profile_policy": {
                        "observed_events": 6,
                        "connect_success_rate": 0.52,
                        "fallback_rate": 0.37,
                        "continuity_success_rate": 0.33,
                        "cross_route_recovery_rate": 0.17,
                        "policy_score": 214,
                        "degraded": True,
                        "advisory_state": "avoid-new-sessions",
                        "recommended_action": "Pause new Helix sessions.",
                        "selection_eligible": False,
                        "new_session_issuable": False,
                        "new_session_posture": "blocked",
                    },
                    "recommended_transport_profile_id": None,
                    "healthy_candidate_count": 0,
                    "eligible_candidate_count": 0,
                    "channel_posture": "blocked",
                    "automatic_reaction": "pause-new-sessions",
                    "pause_recommended": True,
                    "profile_rotation_recommended": True,
                    "recommended_action": "Pause new Helix sessions.",
                },
            },
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.get_rollout_status("rollout-lab-1")
    assert response.policy.active_transport_profile_id == "ptp-lab-edge-v7"
    assert response.policy.active_profile_policy is not None
    assert response.policy.active_profile_policy.advisory_state == "avoid-new-sessions"
    assert response.policy.active_profile_policy.new_session_posture == "blocked"
    assert response.desktop.continuity_observed_events == 5
    assert response.desktop.benchmark_observed_events == 4
    assert response.desktop.throughput_evidence_observed_events == 3
    assert response.desktop.average_benchmark_throughput_kbps == 72500.25
    assert response.desktop.average_relative_throughput_ratio == 1.14
    assert response.desktop.average_relative_open_to_first_byte_gap_ratio == 0.93
    assert response.policy.channel_posture == "blocked"
    assert response.policy.automatic_reaction == "pause-new-sessions"
    assert response.policy.pause_recommended is True
    assert response.policy.profile_rotation_recommended is True
    await client.close()


@pytest.mark.asyncio
async def test_get_rollout_canary_evidence_parses_snapshot():
    def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.url.path
            == "/internal/rollouts/rollout-canary-1/canary-evidence"
        )
        return httpx.Response(
            200,
            json={
                "schema_version": "1.0",
                "rollout_id": "rollout-canary-1",
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
                    "benchmark_observed_events": 1,
                    "throughput_evidence_observed_events": 1,
                    "average_benchmark_throughput_kbps": 81234.5,
                    "average_relative_throughput_ratio": 1.18,
                    "average_relative_open_to_first_byte_gap_ratio": 0.91,
                    "channel_posture": "watch",
                    "active_profile_advisory_state": "watch",
                    "active_profile_new_session_posture": "watch",
                    "applied_automatic_reaction": None,
                    "applied_transport_profile_id": None,
                },
            },
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.get_rollout_canary_evidence("rollout-canary-1")
    assert response.decision == "watch"
    assert response.thresholds.require_throughput_evidence is True
    assert response.snapshot.average_relative_throughput_ratio == 1.18
    assert response.evidence_gaps == ["throughput evidence observations=0"]
    assert response.recommended_follow_up_action == "collect-more-evidence"
    await client.close()


@pytest.mark.asyncio
async def test_report_runtime_event_posts_to_internal_desktop_endpoint():
    observed_path = None
    observed_json = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal observed_path, observed_json
        observed_path = request.url.path
        observed_json = request.read().decode("utf-8")
        assert "desktop-1" in observed_json
        assert "fallback" in observed_json
        return httpx.Response(
            200,
            json={
                "status": "accepted",
                "rollout_id": "rollout-lab-1",
                "event_kind": "fallback",
            },
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.report_runtime_event(
        AdapterDesktopRuntimeEventRequest(
            event_id="bb78087d-5fd4-4efd-bde7-8f83c8c88ac6",
            user_id="user-1",
            desktop_client_id="desktop-1",
            manifest_version_id="de33fcba-b71d-4f5f-82d2-34ae78977e31",
            rollout_id="rollout-lab-1",
            transport_profile_id="ptp-lab-edge-v2",
            event_kind="fallback",
            active_core="sing-box",
            fallback_core="sing-box",
            latency_ms=640,
            route_count=2,
            reason="health gate timeout",
            payload=AdapterDesktopRuntimeEventPayload(
                reason_code="startup-timeout",
                recovery=AdapterDesktopRuntimeEventRecoveryEvidence(
                    same_route_recovered=False,
                    ready_recovery_latency_ms=41,
                    proxy_ready_latency_ms=56,
                ),
                continuity=AdapterDesktopRuntimeEventContinuityEvidence(
                    active_streams=3,
                    continuity_grace_entries=2,
                    successful_continuity_recovers=1,
                ),
            ),
            observed_at="2026-03-31T10:00:00Z",
        )
    )

    assert observed_path == "/internal/desktop/runtime-events"
    assert '"recovery"' in observed_json
    assert '"continuity"' in observed_json
    assert response.status == "accepted"
    assert response.event_kind == "fallback"
    await client.close()


@pytest.mark.asyncio
async def test_report_runtime_benchmark_event_posts_to_internal_desktop_endpoint():
    observed_path = None
    observed_json = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal observed_path, observed_json
        observed_path = request.url.path
        observed_json = request.read().decode("utf-8")
        assert "desktop-1" in observed_json
        assert '"benchmark"' in observed_json
        assert '"relative_throughput_ratio_vs_baseline":1.18' in observed_json
        return httpx.Response(
            200,
            json={
                "status": "accepted",
                "rollout_id": "rollout-lab-1",
                "event_kind": "benchmark",
            },
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    response = await client.report_runtime_event(
        AdapterDesktopRuntimeEventRequest(
            event_id="bb78087d-5fd4-4efd-bde7-8f83c8c88ac6",
            user_id="user-1",
            desktop_client_id="desktop-1",
            manifest_version_id="de33fcba-b71d-4f5f-82d2-34ae78977e31",
            rollout_id="rollout-lab-1",
            transport_profile_id="ptp-lab-edge-v2",
            event_kind="benchmark",
            active_core="helix",
            route_count=2,
            payload=AdapterDesktopRuntimeEventPayload(
                benchmark={
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
                }
            ),
            observed_at="2026-03-31T10:00:00Z",
        )
    )

    assert observed_path == "/internal/desktop/runtime-events"
    assert '"benchmark"' in observed_json
    assert '"throughput_kbps"' in observed_json
    assert response.status == "accepted"
    assert response.event_kind == "benchmark"
    await client.close()


def test_runtime_event_payload_coerces_legacy_flat_benchmark_fields():
    request = AdapterDesktopRuntimeEventRequest.model_validate(
        {
            "event_id": "bb78087d-5fd4-4efd-bde7-8f83c8c88ac6",
            "user_id": "user-1",
            "desktop_client_id": "desktop-1",
            "manifest_version_id": "de33fcba-b71d-4f5f-82d2-34ae78977e31",
            "rollout_id": "rollout-lab-1",
            "transport_profile_id": "ptp-lab-edge-v2",
            "event_kind": "benchmark",
            "active_core": "helix",
            "observed_at": "2026-03-31T10:00:00Z",
            "payload": {
                "benchmark_kind": "target-matrix",
                "baseline_core": "xray",
                "throughput_kbps": 75678.25,
                "relative_throughput_ratio_vs_baseline": 1.12,
                "median_open_to_first_byte_gap_ms": 68,
                "p95_open_to_first_byte_gap_ms": 81,
                "relative_open_to_first_byte_gap_ratio_vs_baseline": 0.94,
                "frame_queue_peak": 7,
                "recent_rtt_p95_ms": 39,
                "custom_tag": "kept",
            },
        }
    )

    assert request.payload.benchmark is not None
    assert request.payload.benchmark.benchmark_kind == "target-matrix"
    assert request.payload.benchmark.baseline_core == "xray"
    assert request.payload.benchmark.throughput_kbps == 75678.25
    assert request.payload.benchmark.relative_throughput_ratio_vs_baseline == 1.12
    assert request.payload.benchmark.median_open_to_first_byte_gap_ms == 68
    assert request.payload.benchmark.p95_open_to_first_byte_gap_ms == 81
    assert request.payload.benchmark.relative_open_to_first_byte_gap_ratio_vs_baseline == 0.94
    assert request.payload.benchmark.frame_queue_peak == 7
    assert request.payload.benchmark.recent_rtt_p95_ms == 39
    assert request.payload.model_extra == {"custom_tag": "kept"}


def test_runtime_event_payload_coerces_legacy_flat_recovery_and_continuity_fields():
    request = AdapterDesktopRuntimeEventRequest.model_validate(
        {
            "event_id": "bb78087d-5fd4-4efd-bde7-8f83c8c88ac6",
            "user_id": "user-1",
            "desktop_client_id": "desktop-1",
            "manifest_version_id": "de33fcba-b71d-4f5f-82d2-34ae78977e31",
            "rollout_id": "rollout-lab-1",
            "transport_profile_id": "ptp-lab-edge-v2",
            "event_kind": "ready",
            "active_core": "helix",
            "observed_at": "2026-03-31T10:00:00Z",
            "payload": {
                "runtime": "embedded-sidecar",
                "ready_recovery_latency_ms": 37,
                "proxy_ready_latency_ms": 49,
                "continuity_grace_active": True,
                "continuity_grace_entries": 2,
                "successful_continuity_recovers": 1,
                "custom_tag": "kept",
            },
        }
    )

    assert request.payload.runtime == "embedded-sidecar"
    assert request.payload.recovery is not None
    assert request.payload.recovery.ready_recovery_latency_ms == 37
    assert request.payload.continuity is not None
    assert request.payload.continuity.continuity_grace_active is True
    assert request.payload.continuity.successful_continuity_recovers == 1
    assert request.payload.model_extra == {"custom_tag": "kept"}


@pytest.mark.asyncio
async def test_resolve_manifest_maps_not_found_to_manifest_unavailable():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": "resource not found: no eligible profile"},
        )

    client = HelixAdapterClient(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(HelixAdapterManifestUnavailableError):
        await client.resolve_manifest(
            AdapterResolveManifestRequest(
                user_id="user-1",
                desktop_client_id="desktop-1",
                entitlement_id="subscription:user-1",
                trace_id="trace-1",
                channel="lab",
                supported_protocol_versions=[1],
            )
        )

    await client.close()
