"""Unit tests for Helix rollout audit task."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")
os.environ.setdefault("METRICS_PROTECT", "false")

from src.services.helix_service import (
    HelixRolloutBatchSummary,
    HelixRolloutDesktopSummary,
    HelixRolloutNodeSummary,
    HelixRolloutPolicySummary,
    HelixTransportProfilePolicySummary,
    HelixRolloutState,
)
from src.tasks.sync.helix_rollouts import audit_helix_rollouts


@pytest.mark.asyncio
async def test_helix_rollout_audit_alerts_on_fallback_spike(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_rollout_min_connect_success_rate = 0.95
    mock_settings.helix_rollout_max_fallback_rate = 0.05
    mock_settings.helix_rollout_min_continuity_success_rate = 0.80
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.20
    mock_settings.helix_alert_state_ttl_seconds = 3600

    degraded_rollout = HelixRolloutState(
        rollout_id="rollout-lab-1",
        channel="lab",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-1",
            manifest_version="manifest-v1",
            target_nodes=2,
            completed_nodes=2,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=2, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.8,
            fallback_rate=0.2,
            continuity_observed_events=2,
            continuity_success_rate=0.75,
            cross_route_recovery_rate=0.25,
        ),
        policy=HelixRolloutPolicySummary(
            pause_on_rollback_spike=True,
            revoke_on_manifest_error=True,
        ),
    )

    with (
        patch(
            "src.tasks.sync.helix_rollouts.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.sync.helix_rollouts.get_redis_client",
            return_value=mock_redis,
        ),
        patch("src.tasks.sync.helix_rollouts.CacheService") as MockCache,
        patch(
            "src.tasks.sync.helix_rollouts.HelixService"
        ) as MockService,
        patch(
            "src.tasks.sync.helix_rollouts.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [degraded_rollout]
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_rollouts()

    assert result["rollouts_checked"] == 1
    assert result["issue_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_rollout_audit_alerts_on_pause_recommendation(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_rollout_min_connect_success_rate = 0.95
    mock_settings.helix_rollout_max_fallback_rate = 0.05
    mock_settings.helix_rollout_min_continuity_success_rate = 0.80
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.20
    mock_settings.helix_alert_state_ttl_seconds = 3600

    advisory_rollout = HelixRolloutState(
        rollout_id="rollout-canary-1",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-7",
            manifest_version="manifest-v7",
            target_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.92,
            fallback_rate=0.03,
            continuity_observed_events=5,
            continuity_success_rate=0.28,
            cross_route_recovery_rate=0.08,
        ),
        policy=HelixRolloutPolicySummary(
            pause_on_rollback_spike=True,
            revoke_on_manifest_error=True,
            active_transport_profile_id="ptp-canary-edge-v9",
            active_profile_policy=HelixTransportProfilePolicySummary(
                observed_events=8,
                connect_success_rate=0.42,
                fallback_rate=0.38,
                continuity_success_rate=0.25,
                cross_route_recovery_rate=0.12,
                policy_score=181,
                degraded=True,
                advisory_state="avoid-new-sessions",
                recommended_action=(
                    "Pause new Helix sessions for rollout rollout-canary-1. "
                    "Transport profile ptp-canary-edge-v9 is marked avoid-new-sessions "
                    "and no healthier compatible profile is available."
                ),
                selection_eligible=False,
                new_session_issuable=False,
                new_session_posture="blocked",
            ),
            healthy_candidate_count=0,
            eligible_candidate_count=0,
            channel_posture="blocked",
            automatic_reaction="pause-new-sessions",
            pause_recommended=True,
            profile_rotation_recommended=True,
            recommended_action=(
                "Pause new Helix sessions for rollout rollout-canary-1. "
                "Transport profile ptp-canary-edge-v9 is marked avoid-new-sessions "
                "and no healthier compatible profile is available."
            ),
        ),
    )

    with (
        patch(
            "src.tasks.sync.helix_rollouts.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.sync.helix_rollouts.get_redis_client",
            return_value=mock_redis,
        ),
        patch("src.tasks.sync.helix_rollouts.CacheService") as MockCache,
        patch(
            "src.tasks.sync.helix_rollouts.HelixService"
        ) as MockService,
        patch(
            "src.tasks.sync.helix_rollouts.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [advisory_rollout]
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_rollouts()

    assert result["rollouts_checked"] == 1
    assert result["issue_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_rollout_audit_alerts_on_continuity_regression(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_rollout_min_connect_success_rate = 0.95
    mock_settings.helix_rollout_max_fallback_rate = 0.05
    mock_settings.helix_rollout_min_continuity_success_rate = 0.85
    mock_settings.helix_rollout_min_cross_route_recovery_rate = 0.25
    mock_settings.helix_alert_state_ttl_seconds = 3600

    continuity_rollout = HelixRolloutState(
        rollout_id="rollout-stable-1",
        channel="stable",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-9",
            manifest_version="manifest-v9",
            target_nodes=3,
            completed_nodes=3,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=3, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.97,
            fallback_rate=0.02,
            continuity_observed_events=6,
            continuity_success_rate=0.5,
            cross_route_recovery_rate=0.17,
        ),
        policy=HelixRolloutPolicySummary(
            pause_on_rollback_spike=True,
            revoke_on_manifest_error=True,
            active_transport_profile_id="ptp-stable-edge-v6",
            active_profile_policy=HelixTransportProfilePolicySummary(
                observed_events=12,
                connect_success_rate=0.97,
                fallback_rate=0.02,
                continuity_success_rate=0.5,
                cross_route_recovery_rate=0.17,
                policy_score=702,
                degraded=False,
                advisory_state="watch",
                recommended_action="Investigate continuity regression before widening rollout.",
                selection_eligible=True,
                new_session_issuable=True,
                new_session_posture="watch",
            ),
            healthy_candidate_count=1,
            eligible_candidate_count=1,
            channel_posture="watch",
            automatic_reaction="observe",
            pause_recommended=False,
            profile_rotation_recommended=False,
            recommended_action="Investigate continuity regression before widening rollout.",
        ),
    )

    with (
        patch(
            "src.tasks.sync.helix_rollouts.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.sync.helix_rollouts.get_redis_client",
            return_value=mock_redis,
        ),
        patch("src.tasks.sync.helix_rollouts.CacheService") as MockCache,
        patch(
            "src.tasks.sync.helix_rollouts.HelixService"
        ) as MockService,
        patch(
            "src.tasks.sync.helix_rollouts.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_active_rollout_states.return_value = [continuity_rollout]
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_rollouts()

    assert result["rollouts_checked"] == 1
    assert result["issue_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    message = mock_telegram.send_admin_alert.call_args.args[0]
    assert "Continuity observations" in message
    assert "cross-route recovery rate=17.00%" in message
