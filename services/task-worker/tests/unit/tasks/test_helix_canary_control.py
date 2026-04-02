"""Unit tests for Helix canary control monitoring task."""

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
    HelixRolloutState,
)
from src.tasks.monitoring.helix_canary_control import audit_helix_canary_control


def build_canary_evidence(
    *,
    rollout_id: str,
    decision: str,
    reasons: list[str] | None = None,
    evidence_gaps: list[str] | None = None,
    applied_reaction: str | None = None,
    throughput_ratio: float | None = 0.97,
    gap_ratio: float | None = 1.04,
    follow_up_action: str | None = None,
    follow_up_severity: str | None = None,
    follow_up_tasks: list[str] | None = None,
) -> HelixRolloutCanaryEvidence:
    return HelixRolloutCanaryEvidence(
        schema_version="1.0",
        rollout_id=rollout_id,
        channel="canary",
        evaluated_at=datetime.now(UTC),
        decision=decision,
        reasons=reasons or [],
        evidence_gaps=evidence_gaps or [],
        recommended_follow_up_action=follow_up_action,
        recommended_follow_up_severity=follow_up_severity,
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
            average_relative_throughput_ratio=throughput_ratio,
            average_relative_open_to_first_byte_gap_ratio=gap_ratio,
            channel_posture="healthy",
            active_profile_advisory_state="healthy",
            active_profile_new_session_posture="preferred",
            applied_automatic_reaction=applied_reaction,
            applied_transport_profile_id=None,
        ),
    )


@pytest.mark.asyncio
async def test_helix_canary_control_alerts_on_hold_channel_paused(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600

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
            fallback_rate=0.08,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="helix-canary-edge-v10",
            channel_posture="blocked",
            applied_automatic_reaction="pause-channel",
            automatic_reaction_trigger_reason="fallback spike",
            automatic_reaction_updated_at=datetime.now(UTC),
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_control.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_control.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_control.TelegramClient"
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
            reasons=["applied actuation=pause-channel"],
            applied_reaction="pause-channel",
            throughput_ratio=0.81,
            gap_ratio=1.29,
            follow_up_action="hold-channel-paused",
            follow_up_severity="critical",
            follow_up_tasks=[
                "Keep new Helix sessions paused on this rollout channel.",
                "Validate node convergence and replacement profile readiness.",
                "Re-run canary evidence before any manual resume decision.",
            ],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_control()

    assert result["rollouts_checked"] == 1
    assert result["actionable_rollouts"] == 1
    assert result["new_actions"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "Hold Channel Paused" in message
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_canary_control_alerts_on_collect_more_evidence(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600

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
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="helix-canary-edge-v11",
            channel_posture="watch",
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_control.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_control.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_control.TelegramClient"
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
            reasons=["continuity observations=2"],
            evidence_gaps=["throughput evidence observations=0"],
            throughput_ratio=None,
            gap_ratio=None,
            follow_up_action="collect-more-evidence",
            follow_up_severity="warning",
            follow_up_tasks=[
                "Run Helix recovery drill and target-matrix benchmarks on the affected desktop cohort.",
                "Capture support bundles until continuity and throughput evidence reach the canary thresholds.",
                "Keep the rollout on watch until evidence gaps are cleared.",
            ],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_control()

    assert result["rollouts_checked"] == 1
    assert result["actionable_rollouts"] == 1
    assert result["new_actions"] == 1
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "Collect More Evidence" in message
    assert "throughput evidence observations=0" in message
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "warning"


@pytest.mark.asyncio
async def test_helix_canary_control_dedupes_repeated_action_state(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600

    rollout = HelixRolloutState(
        rollout_id="rollout-canary-3",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-12",
            manifest_version="manifest-v12",
            target_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.995,
            fallback_rate=0.0,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="helix-canary-edge-v12",
            channel_posture="watch",
        ),
    )

    evidence = build_canary_evidence(
        rollout_id=rollout.rollout_id,
        decision="watch",
        reasons=["continuity observations=2"],
        evidence_gaps=["throughput evidence observations=0"],
        throughput_ratio=None,
        gap_ratio=None,
        follow_up_action="collect-more-evidence",
        follow_up_severity="warning",
        follow_up_tasks=[
            "Run Helix recovery drill and target-matrix benchmarks on the affected desktop cohort.",
            "Capture support bundles until continuity and throughput evidence reach the canary thresholds.",
            "Keep the rollout on watch until evidence gaps are cleared.",
        ],
    )
    expected_signature = "|".join(
        [
            "collect-more-evidence",
            "watch",
            "",
            "",
            "",
            *evidence.reasons,
            *evidence.evidence_gaps,
        ]
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_control.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_control.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_control.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "active": True,
                "action": "collect-more-evidence",
                "signature": expected_signature,
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = evidence
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_control()

    assert result["actionable_rollouts"] == 1
    assert result["new_actions"] == 0
    mock_telegram.send_admin_alert.assert_not_called()


@pytest.mark.asyncio
async def test_helix_canary_control_resolves_when_go_returns(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600

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
            continuity_success_rate=0.98,
            cross_route_recovery_rate=0.45,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="helix-canary-edge-v13",
            channel_posture="healthy",
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_canary_control.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_canary_control.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_canary_control.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_canary_control.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "active": True,
                "action": "hold-channel-paused",
                "signature": "hold-channel-paused|no-go|pause-channel",
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = build_canary_evidence(
            rollout_id=rollout.rollout_id,
            decision="go",
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_canary_control()

    assert result["actionable_rollouts"] == 0
    assert result["cleared_actions"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "Helix Canary Control Cleared" in message
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "resolved"
