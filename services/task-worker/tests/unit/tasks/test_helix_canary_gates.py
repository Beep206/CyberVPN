"""Unit tests for Helix canary gate audit task."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")
os.environ.setdefault("METRICS_PROTECT", "false")

from src.services.helix_service import (
    HelixRolloutBatchSummary,
    HelixRolloutCanaryEvidence,
    HelixRolloutCanarySnapshotSummary,
    HelixRolloutCanaryThresholdSummary,
    HelixRolloutDesktopSummary,
    HelixRolloutNodeSummary,
    HelixRolloutPolicySummary,
    HelixTransportProfilePolicySummary,
    HelixRolloutState,
)
from src.tasks.monitoring.helix_canary_gates import audit_helix_canary_gates


def build_canary_evidence(
    *,
    rollout_id: str,
    decision: str,
    reasons: list[str],
    evidence_gaps: list[str],
    follow_up_action: str | None = None,
    follow_up_tasks: list[str] | None = None,
) -> HelixRolloutCanaryEvidence:
    return HelixRolloutCanaryEvidence(
        schema_version="1.0",
        rollout_id=rollout_id,
        channel="canary",
        evaluated_at=datetime.now(UTC),
        decision=decision,
        reasons=reasons,
        evidence_gaps=evidence_gaps,
        recommended_follow_up_action=follow_up_action,
        recommended_follow_up_severity="warning" if follow_up_action else None,
        recommended_follow_up_tasks=follow_up_tasks or [],
        thresholds=HelixRolloutCanaryThresholdSummary(
            min_connect_success_rate=0.98,
            max_fallback_rate=0.03,
            min_continuity_observations=5,
            require_throughput_evidence=True,
            min_relative_throughput_ratio=0.90,
            max_relative_open_to_first_byte_gap_ratio=1.15,
            min_continuity_success_rate=0.80,
            min_cross_route_recovery_rate=0.20,
        ),
        snapshot=HelixRolloutCanarySnapshotSummary(
            desired_state="running",
            failed_nodes=0,
            rolled_back_nodes=0,
            connect_success_rate=0.99,
            fallback_rate=0.0,
            continuity_observed_events=6,
            continuity_success_rate=0.95,
            cross_route_recovery_rate=0.40,
            benchmark_observed_events=4,
            throughput_evidence_observed_events=4,
            average_benchmark_throughput_kbps=45_200.0,
            average_relative_throughput_ratio=0.97,
            average_relative_open_to_first_byte_gap_ratio=1.04,
            channel_posture="healthy",
            active_profile_advisory_state="healthy",
            active_profile_new_session_posture="preferred",
            applied_automatic_reaction=None,
            applied_transport_profile_id=None,
        ),
    )


@pytest.mark.asyncio
async def test_helix_canary_gate_alerts_no_go_on_applied_pause_channel(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_canary_min_connect_success_rate = 0.98
    mock_settings.helix_canary_max_fallback_rate = 0.03
    mock_settings.helix_canary_min_continuity_observations = 5
    mock_settings.helix_canary_require_throughput_evidence = True
    mock_settings.helix_canary_min_relative_throughput_ratio = 0.90
    mock_settings.helix_canary_max_relative_open_to_first_byte_gap_ratio = 1.15
    mock_settings.helix_rollout_min_continuity_success_rate = 0.80
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.20

    rollout = HelixRolloutState(
        rollout_id="rollout-canary-1",
        channel="canary",
        desired_state="paused",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-10",
            manifest_version="manifest-v10",
            target_nodes=2,
            completed_nodes=1,
            failed_nodes=1,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=1),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.91,
            fallback_rate=0.06,
            continuity_observed_events=7,
            continuity_success_rate=0.51,
            cross_route_recovery_rate=0.11,
            benchmark_observed_events=3,
            throughput_evidence_observed_events=3,
            average_benchmark_throughput_kbps=12500.0,
            average_relative_throughput_ratio=0.82,
            average_relative_open_to_first_byte_gap_ratio=1.32,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-canary-edge-v10",
            channel_posture="blocked",
            applied_automatic_reaction="pause-channel",
            automatic_reaction_updated_at=datetime.now(UTC),
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_gates.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_gates.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = build_canary_evidence(
            rollout_id=rollout.rollout_id,
            decision="no-go",
            reasons=[
                "applied actuation=pause-channel",
                "failed nodes=1",
                "rolled back nodes=1",
                "connect success rate=91.00%",
                "fallback rate=6.00%",
                "continuity success rate=51.00%",
                "cross-route recovery rate=11.00%",
                "relative throughput ratio=0.82",
                "relative open->first-byte gap ratio=1.32",
            ],
            evidence_gaps=[],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_gates()

    assert result["rollouts_checked"] == 1
    assert result["no_go_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_canary_gate_alerts_watch_when_evidence_is_incomplete(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_canary_min_connect_success_rate = 0.98
    mock_settings.helix_canary_max_fallback_rate = 0.03
    mock_settings.helix_canary_min_continuity_observations = 5
    mock_settings.helix_canary_require_throughput_evidence = True
    mock_settings.helix_canary_min_relative_throughput_ratio = 0.90
    mock_settings.helix_canary_max_relative_open_to_first_byte_gap_ratio = 1.15
    mock_settings.helix_rollout_min_continuity_success_rate = 0.80
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.20

    rollout = HelixRolloutState(
        rollout_id="rollout-canary-2",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-11",
            manifest_version="manifest-v11",
            target_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.995,
            fallback_rate=0.0,
            continuity_observed_events=2,
            continuity_success_rate=1.0,
            cross_route_recovery_rate=1.0,
            benchmark_observed_events=0,
            throughput_evidence_observed_events=0,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-canary-edge-v11",
            channel_posture="healthy",
            active_profile_policy=HelixTransportProfilePolicySummary(
                observed_events=5,
                connect_success_rate=0.995,
                fallback_rate=0.0,
                continuity_success_rate=1.0,
                cross_route_recovery_rate=1.0,
                policy_score=930,
                advisory_state="healthy",
                selection_eligible=True,
                new_session_issuable=True,
                new_session_posture="preferred",
            ),
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_gates.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_gates.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = build_canary_evidence(
            rollout_id=rollout.rollout_id,
            decision="watch",
            reasons=["continuity observations=2", "throughput evidence observations=0"],
            evidence_gaps=[
                "continuity observations=2",
                "throughput evidence observations=0",
            ],
            follow_up_action="collect-more-evidence",
            follow_up_tasks=[
                "Run Helix recovery drill on the current canary cohort.",
                "Capture throughput evidence before changing exposure.",
            ],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_gates()

    assert result["rollouts_checked"] == 1
    assert result["watch_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "Follow-up action" in message
    assert "collect-more-evidence" in message
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "warning"


@pytest.mark.asyncio
async def test_helix_canary_gate_resolves_when_rollout_returns_to_go(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_canary_min_connect_success_rate = 0.98
    mock_settings.helix_canary_max_fallback_rate = 0.03
    mock_settings.helix_canary_min_continuity_observations = 0
    mock_settings.helix_canary_require_throughput_evidence = True
    mock_settings.helix_canary_min_relative_throughput_ratio = 0.90
    mock_settings.helix_canary_max_relative_open_to_first_byte_gap_ratio = 1.15
    mock_settings.helix_rollout_min_continuity_success_rate = 0.80
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.20

    rollout = HelixRolloutState(
        rollout_id="rollout-canary-3",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-12",
            manifest_version="manifest-v12",
            target_nodes=2,
            completed_nodes=2,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=2, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.99,
            fallback_rate=0.0,
            continuity_observed_events=6,
            continuity_success_rate=0.95,
            cross_route_recovery_rate=0.40,
            benchmark_observed_events=4,
            throughput_evidence_observed_events=4,
            average_benchmark_throughput_kbps=45200.0,
            average_relative_throughput_ratio=0.97,
            average_relative_open_to_first_byte_gap_ratio=1.04,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-canary-edge-v12",
            channel_posture="healthy",
            active_profile_policy=HelixTransportProfilePolicySummary(
                observed_events=8,
                connect_success_rate=0.99,
                fallback_rate=0.0,
                continuity_success_rate=0.95,
                cross_route_recovery_rate=0.40,
                policy_score=980,
                advisory_state="healthy",
                selection_eligible=True,
                new_session_issuable=True,
                new_session_posture="preferred",
            ),
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_gates.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_gates.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "decision": "watch",
                "signature": "watch|throughput evidence observations=0",
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = build_canary_evidence(
            rollout_id=rollout.rollout_id,
            decision="go",
            reasons=[],
            evidence_gaps=[],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_gates()

    assert result["rollouts_checked"] == 1
    assert result["go_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "resolved"


@pytest.mark.asyncio
async def test_helix_canary_gate_alerts_no_go_on_poor_throughput_evidence(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_canary_min_connect_success_rate = 0.98
    mock_settings.helix_canary_max_fallback_rate = 0.03
    mock_settings.helix_canary_min_continuity_observations = 5
    mock_settings.helix_canary_require_throughput_evidence = True
    mock_settings.helix_canary_min_relative_throughput_ratio = 0.92
    mock_settings.helix_canary_max_relative_open_to_first_byte_gap_ratio = 1.15
    mock_settings.helix_rollout_min_continuity_success_rate = 0.80
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.20

    rollout = HelixRolloutState(
        rollout_id="rollout-canary-4",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-13",
            manifest_version="manifest-v13",
            target_nodes=2,
            completed_nodes=2,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=2, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.995,
            fallback_rate=0.0,
            continuity_observed_events=8,
            continuity_success_rate=0.95,
            cross_route_recovery_rate=0.45,
            benchmark_observed_events=5,
            throughput_evidence_observed_events=5,
            average_benchmark_throughput_kbps=22000.0,
            average_relative_throughput_ratio=0.81,
            average_relative_open_to_first_byte_gap_ratio=1.05,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-canary-edge-v13",
            channel_posture="healthy",
            active_profile_policy=HelixTransportProfilePolicySummary(
                observed_events=10,
                connect_success_rate=0.995,
                fallback_rate=0.0,
                continuity_success_rate=0.95,
                cross_route_recovery_rate=0.45,
                policy_score=995,
                advisory_state="healthy",
                selection_eligible=True,
                new_session_issuable=True,
                new_session_posture="preferred",
            ),
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_gates.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_gates.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_gates.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = build_canary_evidence(
            rollout_id=rollout.rollout_id,
            decision="no-go",
            reasons=["relative throughput ratio=0.81"],
            evidence_gaps=[],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_gates()

    assert result["rollouts_checked"] == 1
    assert result["no_go_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"
