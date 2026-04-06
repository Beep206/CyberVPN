"""Semi-automatic Helix canary control loop."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.cache_service import CacheService
from src.services.helix_service import (
    HelixRolloutCanaryEvidence,
    HelixRolloutState,
    HelixService,
)
from src.services.redis_client import get_redis_client
from src.services.telegram_client import TelegramClient
from src.utils.constants import HELIX_CANARY_CONTROL_KEY

logger = structlog.get_logger(__name__)


def _action_title(action: str) -> str:
    return {
        "hold-channel-paused": "Hold Channel Paused",
        "approve-profile-rotation": "Approve Profile Rotation",
        "collect-more-evidence": "Collect More Evidence",
        "review-watch-signals": "Review Watch Signals",
        "review-canary-blockers": "Review Canary Blockers",
    }.get(action, "Review Canary Control State")


def _format_control_message(
    rollout: HelixRolloutState,
    *,
    action: str,
    severity: str,
    canary_evidence: HelixRolloutCanaryEvidence,
    now: datetime,
    previous_action: str | None = None,
) -> str:
    icon = "🚨" if severity == "critical" else "⚠️"
    header = f"{icon} <b>Helix Canary Control: {_action_title(action)}</b>"
    policy = rollout.policy
    snapshot = canary_evidence.snapshot

    body = [
        header,
        "",
        f"Rollout: <code>{rollout.rollout_id}</code>",
        f"Channel: <code>{rollout.channel}</code>",
        f"Decision: <b>{canary_evidence.decision}</b>",
        f"Action: <b>{action}</b>",
    ]

    if previous_action is not None:
        body.append(f"Previous action: <b>{previous_action}</b>")

    body.extend(
        [
            f"Applied reaction: <b>{policy.applied_automatic_reaction or 'none'}</b>",
            f"Applied target profile: <code>{policy.applied_transport_profile_id or 'none'}</code>",
            f"Active profile: <code>{policy.active_transport_profile_id or 'unknown'}</code>",
            f"Recommended profile: <code>{policy.recommended_transport_profile_id or 'none'}</code>",
            f"Channel posture: <b>{policy.channel_posture}</b>",
            (
                "Active profile posture: <b>"
                f"{snapshot.active_profile_new_session_posture or 'unknown'}"
                "</b>"
            ),
            f"Connect success: <b>{snapshot.connect_success_rate:.2%}</b>",
            f"Fallback rate: <b>{snapshot.fallback_rate:.2%}</b>",
            f"Continuity observations: <b>{snapshot.continuity_observed_events}</b>",
            f"Continuity success: <b>{snapshot.continuity_success_rate:.2%}</b>",
            f"Cross-route recovery: <b>{snapshot.cross_route_recovery_rate:.2%}</b>",
            (
                "Relative throughput ratio: <b>"
                f"{snapshot.average_relative_throughput_ratio:.2f}"
                "</b>"
                if snapshot.average_relative_throughput_ratio is not None
                else "Relative throughput ratio: <b>unavailable</b>"
            ),
            (
                "Relative open->first-byte gap ratio: <b>"
                f"{snapshot.average_relative_open_to_first_byte_gap_ratio:.2f}"
                "</b>"
                if snapshot.average_relative_open_to_first_byte_gap_ratio is not None
                else "Relative open->first-byte gap ratio: <b>unavailable</b>"
            ),
        ]
    )

    if canary_evidence.reasons:
        body.append(f"Reasons: <b>{'; '.join(canary_evidence.reasons)}</b>")
    if canary_evidence.evidence_gaps:
        body.append(
            f"Evidence gaps: <b>{'; '.join(canary_evidence.evidence_gaps)}</b>"
        )

    follow_up_tasks = canary_evidence.recommended_follow_up_tasks or []
    formatted_tasks = "\n".join(
        f"{index}. {task}" for index, task in enumerate(follow_up_tasks, start=1)
    )
    body.extend(
        [
            "Ops follow-up:",
            formatted_tasks or "1. Review the latest formal canary evidence snapshot.",
            f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        ]
    )
    return "\n".join(body)


def _format_control_resolved_message(
    rollout: HelixRolloutState,
    *,
    previous_action: str,
    canary_evidence: HelixRolloutCanaryEvidence,
    now: datetime,
) -> str:
    return (
        "✅ <b>Helix Canary Control Cleared</b>\n\n"
        f"Rollout: <code>{rollout.rollout_id}</code>\n"
        f"Channel: <code>{rollout.channel}</code>\n"
        f"Cleared action: <b>{previous_action}</b>\n"
        f"Decision: <b>{canary_evidence.decision}</b>\n"
        "Next step: resume normal canary review or promotion checks using the latest evidence snapshot.\n"
        f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
    )


@broker.task(task_name="audit_helix_canary_control", queue="monitoring")
async def audit_helix_canary_control() -> dict:
    """Translate formal Helix canary evidence into operational follow-up actions."""
    settings = get_settings()
    if not settings.helix_enabled:
        return {"skipped": True, "reason": "helix_disabled"}

    redis = get_redis_client()
    cache = CacheService(redis)
    alerts_sent = 0
    rollouts_checked = 0
    actionable_rollouts = 0
    new_actions = 0
    cleared_actions = 0
    now = datetime.now(UTC)

    try:
        async with (
            HelixService() as helix,
            TelegramClient() as telegram,
        ):
            rollout_states = await helix.list_active_rollout_states()

            for rollout in rollout_states:
                if rollout.channel != "canary":
                    continue

                rollouts_checked += 1
                canary_evidence = await helix.get_rollout_canary_evidence(
                    rollout.rollout_id
                )
                action = canary_evidence.recommended_follow_up_action
                severity = canary_evidence.recommended_follow_up_severity
                state_key = HELIX_CANARY_CONTROL_KEY.format(
                    rollout_id=rollout.rollout_id
                )
                previous_state = await cache.get(state_key) or {}
                previous_active = bool(previous_state.get("active", False))
                previous_action = previous_state.get("action")
                previous_signature = previous_state.get("signature", "")

                reasons = canary_evidence.reasons
                evidence_gaps = canary_evidence.evidence_gaps
                signature_parts = [
                    action or "",
                    canary_evidence.decision,
                    rollout.policy.applied_automatic_reaction or "",
                    rollout.policy.applied_transport_profile_id or "",
                    rollout.policy.recommended_transport_profile_id or "",
                    *reasons,
                    *evidence_gaps,
                ]
                current_signature = "|".join(signature_parts)

                if action is not None:
                    actionable_rollouts += 1
                    if not previous_active or previous_signature != current_signature:
                        await telegram.send_admin_alert(
                            _format_control_message(
                                rollout,
                                action=action,
                                severity=severity or "warning",
                                canary_evidence=canary_evidence,
                                now=now,
                                previous_action=(
                                    previous_action if previous_action != action else None
                                ),
                            ),
                            severity=severity or "warning",
                        )
                        alerts_sent += 1
                        new_actions += 1
                elif previous_active and previous_action:
                    await telegram.send_admin_alert(
                        _format_control_resolved_message(
                            rollout,
                            previous_action=previous_action,
                            canary_evidence=canary_evidence,
                            now=now,
                        ),
                        severity="resolved",
                    )
                    alerts_sent += 1
                    cleared_actions += 1

                await cache.set(
                    state_key,
                    {
                        "active": action is not None,
                        "action": action,
                        "decision": canary_evidence.decision,
                        "severity": severity,
                        "signature": current_signature,
                        "updated_at": int(now.timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

        logger.info(
            "helix_canary_control_audit_complete",
            rollouts_checked=rollouts_checked,
            actionable_rollouts=actionable_rollouts,
            new_actions=new_actions,
            cleared_actions=cleared_actions,
            alerts_sent=alerts_sent,
        )
        return {
            "skipped": False,
            "rollouts_checked": rollouts_checked,
            "actionable_rollouts": actionable_rollouts,
            "new_actions": new_actions,
            "cleared_actions": cleared_actions,
            "alerts_sent": alerts_sent,
        }
    finally:
        await redis.aclose()
