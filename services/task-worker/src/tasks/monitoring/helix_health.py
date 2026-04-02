"""Helix health audit task."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.cache_service import CacheService
from src.services.helix_service import HelixService
from src.services.redis_client import get_redis_client
from src.services.telegram_client import TelegramClient
from src.utils.constants import (
    HELIX_NODE_HEALTH_KEY,
    HELIX_POLICY_ADVISORY_KEY,
    HELIX_ROLLBACK_AUDIT_KEY,
)

logger = structlog.get_logger(__name__)


@broker.task(task_name="audit_helix_health", queue="monitoring")
async def audit_helix_health() -> dict:
    """Audit stale node heartbeats and rollback spikes for Helix."""
    settings = get_settings()
    if not settings.helix_enabled:
        return {"skipped": True, "reason": "helix_disabled"}

    redis = get_redis_client()
    cache = CacheService(redis)
    alerts_sent = 0
    stale_nodes = 0
    rollback_rollouts = 0
    policy_rollouts = 0
    now = datetime.now(UTC)

    try:
        async with (
            HelixService() as helix,
            TelegramClient() as telegram,
        ):
            nodes = await helix.list_nodes()
            rollout_ids = sorted(
                {
                    node.active_rollout_id
                    for node in nodes
                    if node.transport_enabled and node.active_rollout_id
                }
            )
            rollout_states = {
                rollout_id: await helix.get_rollout_status(rollout_id)
                for rollout_id in rollout_ids
            }

            for node in nodes:
                if not node.transport_enabled or not node.active_rollout_id:
                    continue

                heartbeat_age_seconds = None
                if node.last_heartbeat_at is not None:
                    heartbeat_age_seconds = max(
                        int((now - node.last_heartbeat_at).total_seconds()), 0
                    )

                is_stale = (
                    node.last_heartbeat_at is None
                    or heartbeat_age_seconds is None
                    or heartbeat_age_seconds
                    > settings.helix_stale_heartbeat_seconds
                )
                state_key = HELIX_NODE_HEALTH_KEY.format(
                    node_id=node.remnawave_node_id
                )
                previous_state = await cache.get(state_key) or {}
                was_stale = bool(previous_state.get("stale", False))

                if is_stale:
                    stale_nodes += 1
                    if not was_stale:
                        message = (
                            "🚨 <b>Helix Node Heartbeat Stale</b>\n\n"
                            f"Node: <code>{node.node_name}</code>\n"
                            f"Node ID: <code>{node.remnawave_node_id}</code>\n"
                            f"Rollout: <code>{node.active_rollout_id}</code>\n"
                            f"Heartbeat age: <b>{heartbeat_age_seconds if heartbeat_age_seconds is not None else 'missing'}s</b>\n"
                            f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
                        )
                        await telegram.send_admin_alert(message, severity="critical")
                        alerts_sent += 1
                elif was_stale:
                    message = (
                        "✅ <b>Helix Node Recovered</b>\n\n"
                        f"Node: <code>{node.node_name}</code>\n"
                        f"Node ID: <code>{node.remnawave_node_id}</code>\n"
                        f"Rollout: <code>{node.active_rollout_id}</code>\n"
                        f"Recovered at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
                    )
                    await telegram.send_admin_alert(message, severity="resolved")
                    alerts_sent += 1

                await cache.set(
                    state_key,
                    {
                        "stale": is_stale,
                        "heartbeat_age_seconds": heartbeat_age_seconds,
                        "updated_at": int(now.timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

            for rollout_id, rollout in rollout_states.items():
                has_rollback_issue = (
                    rollout.nodes.rolled_back
                    >= settings.helix_rollback_alert_threshold
                )
                state_key = HELIX_ROLLBACK_AUDIT_KEY.format(
                    rollout_id=rollout_id
                )
                previous_state = await cache.get(state_key) or {}
                had_issue = bool(previous_state.get("rollback_issue", False))

                if has_rollback_issue:
                    rollback_rollouts += 1
                    if not had_issue:
                        message = (
                            "🚨 <b>Helix Rollback Spike</b>\n\n"
                            f"Rollout: <code>{rollout_id}</code>\n"
                            f"Channel: <code>{rollout.channel}</code>\n"
                            f"Rolled back nodes: <b>{rollout.nodes.rolled_back}</b>\n"
                            f"Stale nodes: <b>{rollout.nodes.stale}</b>\n"
                            f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
                        )
                        await telegram.send_admin_alert(message, severity="critical")
                        alerts_sent += 1
                elif had_issue:
                    message = (
                        "✅ <b>Helix Rollback Pressure Resolved</b>\n\n"
                        f"Rollout: <code>{rollout_id}</code>\n"
                        f"Channel: <code>{rollout.channel}</code>\n"
                        f"Recovered at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
                    )
                    await telegram.send_admin_alert(message, severity="resolved")
                    alerts_sent += 1

                await cache.set(
                    state_key,
                    {
                        "rollback_issue": has_rollback_issue,
                        "rolled_back_nodes": rollout.nodes.rolled_back,
                        "updated_at": int(now.timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

                has_policy_issue = rollout.policy.automatic_reaction in {
                    "rotate-new-sessions",
                    "pause-new-sessions",
                    "rotate-profile-now",
                    "pause-channel",
                } or rollout.policy.pause_recommended
                policy_state_key = HELIX_POLICY_ADVISORY_KEY.format(
                    rollout_id=rollout_id
                )
                previous_policy_state = await cache.get(policy_state_key) or {}
                had_policy_issue = bool(
                    previous_policy_state.get("policy_issue", False)
                )

                if has_policy_issue:
                    policy_rollouts += 1
                    if not had_policy_issue:
                        policy = rollout.policy.active_profile_policy
                        message = (
                            "🚨 <b>Helix Rollout Policy Stop Condition</b>\n\n"
                            f"Rollout: <code>{rollout_id}</code>\n"
                            f"Channel: <code>{rollout.channel}</code>\n"
                            f"Active profile: <code>{rollout.policy.active_transport_profile_id or 'unknown'}</code>\n"
                            f"Channel posture: <b>{rollout.policy.channel_posture}</b>\n"
                            f"Automatic reaction: <b>{rollout.policy.automatic_reaction}</b>\n"
                            f"Applied reaction: <b>{rollout.policy.applied_automatic_reaction or 'none'}</b>\n"
                            f"Applied target profile: <code>{rollout.policy.applied_transport_profile_id or 'none'}</code>\n"
                            f"Suppressed candidates: <b>{rollout.policy.suppressed_candidate_count}</b>\n"
                            f"Active profile suppressed: <b>{rollout.policy.active_profile_suppressed}</b>\n"
                            f"Advisory state: <b>{policy.advisory_state if policy else 'unknown'}</b>\n"
                            f"Policy score: <b>{policy.policy_score if policy else 'n/a'}</b>\n"
                            f"New-session posture: <b>{policy.new_session_posture if policy else 'unknown'}</b>\n"
                            f"New-session issuable: <b>{policy.new_session_issuable if policy else 'unknown'}</b>\n"
                            f"Suppression window active: <b>{policy.suppression_window_active if policy else 'unknown'}</b>\n"
                            f"Pause recommended: <b>{rollout.policy.pause_recommended}</b>\n"
                            f"Action: {rollout.policy.recommended_action or 'Pause or rotate the active Helix profile before widening exposure.'}\n"
                            f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
                        )
                        await telegram.send_admin_alert(message, severity="critical")
                        alerts_sent += 1
                elif had_policy_issue:
                    message = (
                        "✅ <b>Helix Policy Advisory Resolved</b>\n\n"
                        f"Rollout: <code>{rollout_id}</code>\n"
                        f"Channel: <code>{rollout.channel}</code>\n"
                        f"Recovered at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
                    )
                    await telegram.send_admin_alert(message, severity="resolved")
                    alerts_sent += 1

                await cache.set(
                    policy_state_key,
                    {
                        "policy_issue": has_policy_issue,
                        "channel_posture": rollout.policy.channel_posture,
                        "automatic_reaction": rollout.policy.automatic_reaction,
                        "applied_automatic_reaction": rollout.policy.applied_automatic_reaction,
                        "applied_transport_profile_id": rollout.policy.applied_transport_profile_id,
                        "suppressed_candidate_count": rollout.policy.suppressed_candidate_count,
                        "active_profile_suppressed": rollout.policy.active_profile_suppressed,
                        "advisory_state": (
                            rollout.policy.active_profile_policy.advisory_state
                            if rollout.policy.active_profile_policy is not None
                            else None
                        ),
                        "new_session_posture": (
                            rollout.policy.active_profile_policy.new_session_posture
                            if rollout.policy.active_profile_policy is not None
                            else None
                        ),
                        "pause_recommended": rollout.policy.pause_recommended,
                        "new_session_issuable": (
                            rollout.policy.active_profile_policy.new_session_issuable
                            if rollout.policy.active_profile_policy is not None
                            else None
                        ),
                        "suppression_window_active": (
                            rollout.policy.active_profile_policy.suppression_window_active
                            if rollout.policy.active_profile_policy is not None
                            else None
                        ),
                        "updated_at": int(now.timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

        logger.info(
            "helix_health_audit_complete",
            nodes_checked=len(nodes),
            stale_nodes=stale_nodes,
            rollback_rollouts=rollback_rollouts,
            policy_rollouts=policy_rollouts,
            alerts_sent=alerts_sent,
        )
        return {
            "skipped": False,
            "nodes_checked": len(nodes),
            "stale_nodes": stale_nodes,
            "rollback_rollouts": rollback_rollouts,
            "policy_rollouts": policy_rollouts,
            "alerts_sent": alerts_sent,
        }
    finally:
        await redis.aclose()
