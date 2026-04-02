"""Unit tests for Helix actuation monitoring task."""

import os
from datetime import UTC, datetime, timedelta
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
from src.tasks.monitoring.helix_actuations import audit_helix_actuations


def build_canary_evidence(
    *,
    rollout_id: str,
    decision: str,
    follow_up_action: str | None = None,
    follow_up_tasks: list[str] | None = None,
) -> HelixRolloutCanaryEvidence:
    return HelixRolloutCanaryEvidence(
        schema_version="1.0",
        rollout_id=rollout_id,
        channel="canary",
        evaluated_at=datetime.now(UTC),
        decision=decision,
        reasons=["relative throughput ratio=0.82"] if decision == "no-go" else [],
        evidence_gaps=[],
        recommended_follow_up_action=follow_up_action,
        recommended_follow_up_severity="critical" if follow_up_action else None,
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
            average_benchmark_throughput_kbps=45200.0,
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
async def test_helix_actuation_audit_alerts_when_reaction_first_applied(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_actuation_escalation_seconds = 900

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
            connect_success_rate=0.62,
            fallback_rate=0.28,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-canary-edge-v10",
            channel_posture="blocked",
            applied_automatic_reaction="pause-channel",
            automatic_reaction_trigger_reason="fallback spike and continuity collapse",
            automatic_reaction_updated_at=datetime.now(UTC),
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_actuations.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_actuations.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_actuations.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_actuations.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_actuations.TelegramClient"
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
            follow_up_action="hold-channel-paused",
            follow_up_tasks=[
                "Keep new Helix sessions paused on this rollout channel.",
                "Validate replacement profile readiness.",
            ],
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_actuations()

    assert result["active_rollouts"] == 1
    assert result["newly_applied"] == 1
    assert result["escalated"] == 0
    mock_telegram.send_admin_alert.assert_called_once()
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "Canary follow-up action" in message
    assert "hold-channel-paused" in message
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_actuation_audit_escalates_pending_rotation(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_actuation_escalation_seconds = 900

    updated_at = datetime.now(UTC) - timedelta(minutes=30)
    rollout = HelixRolloutState(
        rollout_id="rollout-stable-1",
        channel="stable",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-12",
            manifest_version="manifest-v12",
            target_nodes=3,
            completed_nodes=2,
            failed_nodes=1,
        ),
        nodes=HelixRolloutNodeSummary(healthy=2, stale=0, rolled_back=1),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.88,
            fallback_rate=0.07,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-stable-edge-v12",
            channel_posture="degraded",
            applied_automatic_reaction="rotate-profile-now",
            applied_transport_profile_id="ptp-stable-edge-v13",
            automatic_reaction_trigger_reason="continuity recovery regression",
            automatic_reaction_updated_at=updated_at,
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_actuations.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_actuations.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_actuations.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_actuations.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_actuations.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "active": True,
                "signature": "rotate-profile-now|ptp-stable-edge-v13",
                "reaction": "rotate-profile-now",
                "escalated": False,
            }
        )
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [rollout]
        mock_service.get_rollout_canary_evidence.return_value = build_canary_evidence(
            rollout_id=rollout.rollout_id,
            decision="no-go",
        )
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_actuations()

    assert result["active_rollouts"] == 1
    assert result["newly_applied"] == 0
    assert result["escalated"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "rotation actuation is still pending" in message
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_actuation_audit_alerts_when_reaction_clears(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_alert_state_ttl_seconds = 3600
    mock_settings.helix_actuation_escalation_seconds = 900

    rollout = HelixRolloutState(
        rollout_id="rollout-lab-2",
        channel="lab",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-4",
            manifest_version="manifest-v4",
            target_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.99,
            fallback_rate=0.0,
        ),
        policy=HelixRolloutPolicySummary(
            active_transport_profile_id="ptp-lab-edge-v4",
            channel_posture="healthy",
            automatic_reaction_updated_at=None,
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_actuations.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_actuations.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_actuations.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_actuations.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_actuations.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(
            return_value={
                "active": True,
                "signature": "pause-channel|",
                "reaction": "pause-channel",
                "escalated": True,
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

        result = await audit_helix_actuations()

    assert result["active_rollouts"] == 0
    assert result["recovered"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "resolved"
