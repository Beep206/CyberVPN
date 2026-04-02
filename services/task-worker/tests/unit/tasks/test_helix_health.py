"""Unit tests for Helix health monitoring task."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")
os.environ.setdefault("METRICS_PROTECT", "false")

from src.services.helix_service import (
    HelixNodeRecord,
    HelixRolloutBatchSummary,
    HelixRolloutDesktopSummary,
    HelixRolloutNodeSummary,
    HelixRolloutPolicySummary,
    HelixTransportProfilePolicySummary,
    HelixRolloutState,
)
from src.tasks.monitoring.helix_health import audit_helix_health


@pytest.mark.asyncio
async def test_helix_health_alerts_on_stale_node(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_stale_heartbeat_seconds = 180
    mock_settings.helix_rollback_alert_threshold = 1
    mock_settings.helix_alert_state_ttl_seconds = 3600

    stale_node = HelixNodeRecord(
        remnawave_node_id="node-1",
        node_name="PT Edge EU",
        transport_enabled=True,
        rollout_channel="lab",
        active_rollout_id="rollout-lab-1",
        last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=600),
        daemon_version="v0.1.0",
    )
    healthy_rollout = HelixRolloutState(
        rollout_id="rollout-lab-1",
        channel="lab",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-1",
            manifest_version="manifest-v1",
            target_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=1.0,
            fallback_rate=0.0,
            continuity_observed_events=1,
        ),
        policy=HelixRolloutPolicySummary(
            pause_on_rollback_spike=True,
            revoke_on_manifest_error=True,
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_health.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_health.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_health.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_health.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_health.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=[None, None, None])
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_nodes.return_value = [stale_node]
        mock_service.get_rollout_status.return_value = healthy_rollout
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_health()

    assert result["stale_nodes"] == 1
    assert result["rollback_rollouts"] == 0
    assert result["policy_rollouts"] == 0
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_health_alerts_on_rollback_spike(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_stale_heartbeat_seconds = 180
    mock_settings.helix_rollback_alert_threshold = 1
    mock_settings.helix_alert_state_ttl_seconds = 3600

    healthy_node = HelixNodeRecord(
        remnawave_node_id="node-1",
        node_name="PT Edge EU",
        transport_enabled=True,
        rollout_channel="canary",
        active_rollout_id="rollout-canary-1",
        last_heartbeat_at=datetime.now(UTC),
        daemon_version="v0.1.0",
    )
    rollback_rollout = HelixRolloutState(
        rollout_id="rollout-canary-1",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-1",
            manifest_version="manifest-v2",
            target_nodes=2,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=2),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.5,
            fallback_rate=0.5,
            continuity_observed_events=1,
        ),
        policy=HelixRolloutPolicySummary(
            pause_on_rollback_spike=True,
            revoke_on_manifest_error=True,
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_health.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_health.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_health.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_health.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_health.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=[None, None, None])
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_nodes.return_value = [healthy_node]
        mock_service.get_rollout_status.return_value = rollback_rollout
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_health()

    assert result["stale_nodes"] == 0
    assert result["rollback_rollouts"] == 1
    assert result["policy_rollouts"] == 0
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"


@pytest.mark.asyncio
async def test_helix_health_alerts_on_policy_stop_condition(
    mock_redis, mock_telegram, mock_settings
):
    mock_settings.helix_enabled = True
    mock_settings.helix_stale_heartbeat_seconds = 180
    mock_settings.helix_rollback_alert_threshold = 2
    mock_settings.helix_alert_state_ttl_seconds = 3600

    healthy_node = HelixNodeRecord(
        remnawave_node_id="node-1",
        node_name="PT Edge EU",
        transport_enabled=True,
        rollout_channel="canary",
        active_rollout_id="rollout-canary-2",
        last_heartbeat_at=datetime.now(UTC),
        daemon_version="v0.1.0",
    )
    advisory_rollout = HelixRolloutState(
        rollout_id="rollout-canary-2",
        channel="canary",
        desired_state="running",
        current_batch=HelixRolloutBatchSummary(
            batch_id="batch-2",
            manifest_version="manifest-v5",
            target_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
        ),
        nodes=HelixRolloutNodeSummary(healthy=1, stale=0, rolled_back=0),
        desktop=HelixRolloutDesktopSummary(
            connect_success_rate=0.88,
            fallback_rate=0.1,
            continuity_observed_events=5,
            continuity_success_rate=0.31,
            cross_route_recovery_rate=0.12,
        ),
        policy=HelixRolloutPolicySummary(
            pause_on_rollback_spike=True,
            revoke_on_manifest_error=True,
            active_transport_profile_id="ptp-canary-edge-v5",
            active_profile_policy=HelixTransportProfilePolicySummary(
                observed_events=8,
                connect_success_rate=0.49,
                fallback_rate=0.37,
                continuity_success_rate=0.31,
                cross_route_recovery_rate=0.12,
                policy_score=205,
                degraded=True,
                advisory_state="avoid-new-sessions",
                recommended_action="Pause or rotate this Helix profile.",
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
            recommended_action="Pause or rotate this Helix profile.",
        ),
    )

    with (
        patch(
            "src.tasks.monitoring.helix_health.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.monitoring.helix_health.get_redis_client",
            return_value=mock_redis,
        ),
        patch(
            "src.tasks.monitoring.helix_health.CacheService"
        ) as MockCache,
        patch(
            "src.tasks.monitoring.helix_health.HelixService"
        ) as MockService,
        patch(
            "src.tasks.monitoring.helix_health.TelegramClient"
        ) as MockTelegram,
    ):
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=[None, None, None])
        mock_cache.set = AsyncMock()
        MockCache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.list_nodes.return_value = [healthy_node]
        mock_service.get_rollout_status.return_value = advisory_rollout
        MockService.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        MockService.return_value.__aexit__ = AsyncMock(return_value=False)

        MockTelegram.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        MockTelegram.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await audit_helix_health()

    assert result["stale_nodes"] == 0
    assert result["rollback_rollouts"] == 0
    assert result["policy_rollouts"] == 1
    mock_telegram.send_admin_alert.assert_called_once()
    assert mock_telegram.send_admin_alert.call_args.kwargs["severity"] == "critical"
