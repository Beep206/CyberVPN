"""Unit tests for Helix worker service."""

import os

import httpx
import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")
os.environ.setdefault("METRICS_PROTECT", "false")

from src.services.helix_service import HelixService


@pytest.mark.asyncio
async def test_list_nodes_sends_internal_token_and_parses_response():
    observed_header = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal observed_header
        observed_header = request.headers.get("x-internal-token")
        assert request.url.path == "/admin/nodes"
        return httpx.Response(
            200,
            json=[
                {
                    "remnawave_node_id": "node-1",
                    "node_name": "PT Edge EU",
                    "transport_enabled": True,
                    "rollout_channel": "lab",
                    "active_rollout_id": "rollout-lab-1",
                    "last_heartbeat_at": "2026-03-31T10:00:00Z",
                    "daemon_version": "v0.1.0",
                }
            ],
        )

    async with HelixService(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    ) as service:
        nodes = await service.list_nodes()

    assert observed_header == "adapter-token"
    assert len(nodes) == 1
    assert nodes[0].remnawave_node_id == "node-1"
    assert nodes[0].transport_enabled is True


@pytest.mark.asyncio
async def test_list_active_rollout_states_deduplicates_rollout_ids():
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/admin/nodes":
            return httpx.Response(
                200,
                json=[
                    {
                        "remnawave_node_id": "node-1",
                        "node_name": "PT Edge EU",
                        "transport_enabled": True,
                        "rollout_channel": "lab",
                        "active_rollout_id": "rollout-lab-1",
                    },
                    {
                        "remnawave_node_id": "node-2",
                        "node_name": "PT Edge US",
                        "transport_enabled": True,
                        "rollout_channel": "lab",
                        "active_rollout_id": "rollout-lab-1",
                    },
                ],
            )

        assert request.url.path == "/internal/rollouts/rollout-lab-1/status"
        return httpx.Response(
            200,
            json={
                "rollout_id": "rollout-lab-1",
                "channel": "lab",
                "desired_state": "running",
                "current_batch": {
                    "batch_id": "batch-1",
                    "manifest_version": "manifest-v1",
                    "target_nodes": 2,
                    "completed_nodes": 2,
                    "failed_nodes": 0,
                },
                "nodes": {"healthy": 2, "stale": 0, "rolled_back": 0},
                "desktop": {
                    "connect_success_rate": 1.0,
                    "fallback_rate": 0.0,
                    "continuity_observed_events": 4,
                    "continuity_success_rate": 1.0,
                    "cross_route_recovery_rate": 0.5,
                },
                "policy": {
                    "pause_on_rollback_spike": True,
                    "revoke_on_manifest_error": True,
                    "active_transport_profile_id": "ptp-lab-edge-v2",
                    "active_profile_policy": {
                        "observed_events": 6,
                        "connect_success_rate": 0.98,
                        "fallback_rate": 0.02,
                        "continuity_success_rate": 0.92,
                        "cross_route_recovery_rate": 0.61,
                        "policy_score": 913,
                        "degraded": False,
                        "advisory_state": "healthy",
                        "selection_eligible": True,
                        "new_session_issuable": True,
                        "new_session_posture": "preferred",
                    },
                    "recommended_transport_profile_id": None,
                    "healthy_candidate_count": 1,
                    "eligible_candidate_count": 1,
                    "channel_posture": "healthy",
                    "automatic_reaction": "none",
                    "pause_recommended": False,
                    "profile_rotation_recommended": False,
                    "recommended_action": None,
                },
            },
        )

    async with HelixService(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    ) as service:
        rollouts = await service.list_active_rollout_states()

    assert requests.count("/admin/nodes") == 1
    assert requests.count("/internal/rollouts/rollout-lab-1/status") == 1
    assert len(rollouts) == 1
    assert rollouts[0].rollout_id == "rollout-lab-1"
    assert rollouts[0].desktop.continuity_observed_events == 4
    assert rollouts[0].policy.active_transport_profile_id == "ptp-lab-edge-v2"
    assert rollouts[0].policy.active_profile_policy is not None
    assert rollouts[0].policy.active_profile_policy.policy_score == 913
    assert rollouts[0].policy.active_profile_policy.new_session_posture == "preferred"
    assert rollouts[0].policy.channel_posture == "healthy"
    assert rollouts[0].policy.automatic_reaction == "none"


@pytest.mark.asyncio
async def test_get_rollout_canary_evidence_parses_formal_snapshot():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/rollouts/rollout-canary-1/canary-evidence"
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

    async with HelixService(
        base_url="http://adapter.test",
        token="adapter-token",
        transport=httpx.MockTransport(handler),
    ) as service:
        evidence = await service.get_rollout_canary_evidence("rollout-canary-1")

    assert evidence.decision == "watch"
    assert evidence.thresholds.require_throughput_evidence is True
    assert evidence.snapshot.average_relative_throughput_ratio == 1.18
    assert evidence.evidence_gaps == ["throughput evidence observations=0"]
    assert evidence.recommended_follow_up_action == "collect-more-evidence"
