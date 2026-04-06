"""Helix rollout audit task."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.cache_service import CacheService
from src.services.helix_service import HelixService
from src.services.redis_client import get_redis_client
from src.services.telegram_client import TelegramClient
from src.utils.constants import HELIX_ROLLOUT_AUDIT_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="audit_helix_rollouts", queue="sync")
async def audit_helix_rollouts() -> dict:
    """Audit active Helix rollouts and alert on degraded rollout quality."""
    settings = get_settings()
    if not settings.helix_enabled:
        return {"skipped": True, "reason": "helix_disabled"}

    redis = get_redis_client()
    cache = CacheService(redis)
    alerts_sent = 0
    issue_rollouts = 0

    try:
        async with (
            HelixService() as helix,
            TelegramClient() as telegram,
        ):
            rollout_states = await helix.list_active_rollout_states()

            for rollout in rollout_states:
                issue_codes: list[str] = []
                reasons: list[str] = []
                active_profile_policy = rollout.policy.active_profile_policy
                desktop_signal_present = (
                    rollout.desktop.connect_success_rate > 0
                    or rollout.desktop.fallback_rate > 0
                )
                continuity_signal_present = (
                    rollout.desktop.continuity_observed_events > 0
                )

                if rollout.current_batch.failed_nodes > 0:
                    issue_codes.append("failed-nodes")
                    reasons.append(f"failed nodes={rollout.current_batch.failed_nodes}")

                if (
                    desktop_signal_present
                    and rollout.desktop.connect_success_rate
                    < settings.helix_rollout_min_connect_success_rate
                ):
                    issue_codes.append("connect-success")
                    reasons.append(
                        "connect success rate="
                        f"{rollout.desktop.connect_success_rate:.2%}"
                    )

                if (
                    desktop_signal_present
                    and rollout.desktop.fallback_rate
                    > settings.helix_rollout_max_fallback_rate
                ):
                    issue_codes.append("fallback-rate")
                    reasons.append(f"fallback rate={rollout.desktop.fallback_rate:.2%}")

                if (
                    continuity_signal_present
                    and rollout.desktop.continuity_success_rate
                    < settings.helix_rollout_min_continuity_success_rate
                ):
                    issue_codes.append("continuity-success")
                    reasons.append(
                        "continuity success rate="
                        f"{rollout.desktop.continuity_success_rate:.2%}"
                    )

                if (
                    continuity_signal_present
                    and rollout.desktop.cross_route_recovery_rate
                    < settings.helix_rollout_min_cross_route_recovery_rate
                ):
                    issue_codes.append("cross-route-recovery")
                    reasons.append(
                        "cross-route recovery rate="
                        f"{rollout.desktop.cross_route_recovery_rate:.2%}"
                    )

                if rollout.policy.profile_rotation_recommended:
                    issue_codes.append(
                        f"auto-{rollout.policy.automatic_reaction or 'profile-rotation'}"
                    )
                    reasons.append(
                        rollout.policy.recommended_action
                        or (
                            "active profile="
                            f"{rollout.policy.active_transport_profile_id or 'unknown'} "
                            f"state={active_profile_policy.advisory_state if active_profile_policy else 'unknown'}"
                        )
                    )

                if rollout.policy.pause_recommended:
                    if rollout.policy.automatic_reaction not in {
                        "pause-new-sessions",
                        "pause-channel",
                    }:
                        issue_codes.append("pause-recommended")
                        reasons.append(
                            rollout.policy.recommended_action
                            or (
                                "pause recommended for profile "
                                f"{rollout.policy.active_transport_profile_id or 'unknown'}"
                            )
                        )

                if active_profile_policy is not None and (
                    active_profile_policy.advisory_state
                    in {"degraded", "avoid-new-sessions"}
                ):
                    issue_codes.append(
                        f"policy-{active_profile_policy.advisory_state}"
                    )
                    reasons.append(
                        "policy advisory="
                        f"{active_profile_policy.advisory_state}"
                        f" posture={active_profile_policy.new_session_posture}"
                    )

                audit_key = HELIX_ROLLOUT_AUDIT_KEY.format(
                    rollout_id=rollout.rollout_id
                )
                previous_state = await cache.get(audit_key) or {}
                previous_signature = previous_state.get("issue_signature", "")
                current_signature = "|".join(issue_codes)

                if issue_codes:
                    issue_rollouts += 1
                    if previous_signature != current_signature:
                        message = (
                            "🚨 <b>Helix Rollout Advisory</b>\n\n"
                            f"Rollout: <code>{rollout.rollout_id}</code>\n"
                            f"Channel: <code>{rollout.channel}</code>\n"
                            f"Issues: <b>{', '.join(reasons)}</b>\n"
                            f"Active profile: <code>{rollout.policy.active_transport_profile_id or 'unknown'}</code>\n"
                            f"Recommended profile: <code>{rollout.policy.recommended_transport_profile_id or 'none'}</code>\n"
                            f"Channel posture: <b>{rollout.policy.channel_posture}</b>\n"
                            f"Automatic reaction: <b>{rollout.policy.automatic_reaction}</b>\n"
                            f"Applied reaction: <b>{rollout.policy.applied_automatic_reaction or 'none'}</b>\n"
                            f"Applied target profile: <code>{rollout.policy.applied_transport_profile_id or 'none'}</code>\n"
                            f"Suppressed candidates: <b>{rollout.policy.suppressed_candidate_count}</b>\n"
                            f"Active profile suppressed: <b>{rollout.policy.active_profile_suppressed}</b>\n"
                            f"Policy score: <b>{active_profile_policy.policy_score if active_profile_policy else 'n/a'}</b>\n"
                            f"Advisory state: <b>{active_profile_policy.advisory_state if active_profile_policy else 'unknown'}</b>\n"
                            f"New-session posture: <b>{active_profile_policy.new_session_posture if active_profile_policy else 'unknown'}</b>\n"
                            f"New-session issuable: <b>{active_profile_policy.new_session_issuable if active_profile_policy else 'unknown'}</b>\n"
                            f"Suppression window active: <b>{active_profile_policy.suppression_window_active if active_profile_policy else 'unknown'}</b>\n"
                            f"Connect success: <b>{rollout.desktop.connect_success_rate:.2%}</b>\n"
                            f"Fallback rate: <b>{rollout.desktop.fallback_rate:.2%}</b>\n"
                            f"Continuity observations: <b>{rollout.desktop.continuity_observed_events}</b>\n"
                            f"Continuity success: <b>{rollout.desktop.continuity_success_rate:.2%}</b>\n"
                            f"Cross-route recovery: <b>{rollout.desktop.cross_route_recovery_rate:.2%}</b>\n"
                            f"Action: {rollout.policy.recommended_action or 'Investigate rollout policy and quality signals.'}"
                        )
                        await telegram.send_admin_alert(message, severity="critical")
                        alerts_sent += 1

                elif previous_signature:
                    message = (
                        "✅ <b>Helix Rollout Recovered</b>\n\n"
                        f"Rollout: <code>{rollout.rollout_id}</code>\n"
                        f"Channel: <code>{rollout.channel}</code>\n"
                        f"Recovered at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
                    )
                    await telegram.send_admin_alert(message, severity="resolved")
                    alerts_sent += 1

                await cache.set(
                    audit_key,
                    {
                        "issue_signature": current_signature,
                        "issue_active": bool(issue_codes),
                        "updated_at": int(datetime.now(UTC).timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

        logger.info(
            "helix_rollout_audit_complete",
            rollouts_checked=len(rollout_states),
            issue_rollouts=issue_rollouts,
            alerts_sent=alerts_sent,
        )
        return {
            "skipped": False,
            "rollouts_checked": len(rollout_states),
            "issue_rollouts": issue_rollouts,
            "alerts_sent": alerts_sent,
        }
    finally:
        await redis.aclose()
