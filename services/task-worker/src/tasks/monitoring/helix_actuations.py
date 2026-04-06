"""Helix actuation lifecycle audit task."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.cache_service import CacheService
from src.services.helix_service import (
    HelixRolloutCanaryEvidence,
    HelixService,
    HelixRolloutState,
)
from src.services.redis_client import get_redis_client
from src.services.telegram_client import TelegramClient
from src.utils.constants import HELIX_ACTUATION_AUDIT_KEY

logger = structlog.get_logger(__name__)


def _format_followup_tasks(rollout: HelixRolloutState) -> str:
    policy = rollout.policy
    if policy.applied_automatic_reaction == "pause-channel":
        return (
            "1. Keep new Helix sessions paused for this channel.\n"
            "2. Publish or approve a healthier replacement profile before resume.\n"
            "3. Re-run canary evidence on the affected route/profile combination."
        )

    target_profile = policy.applied_transport_profile_id or "replacement profile"
    return (
        "1. Confirm nodes and desktop manifests converge on "
        f"<code>{target_profile}</code>.\n"
        "2. Watch continuity and fallback rates during the next release window.\n"
        "3. Revoke or demote the unhealthy source profile once recovery is stable."
    )


def _describe_escalation(
    rollout: HelixRolloutState,
    *,
    age_seconds: int | None,
) -> str | None:
    policy = rollout.policy
    reaction = policy.applied_automatic_reaction
    if reaction is None:
        return None

    threshold = age_seconds is not None and age_seconds > 0
    if not threshold:
        return None

    if reaction == "pause-channel":
        if rollout.desired_state != "paused":
            return "pause actuation applied but rollout desired state is not paused"
        return (
            "channel remains paused after the escalation window and still needs "
            "profile rotation or manual resume approval"
        )

    if reaction == "rotate-profile-now":
        target_profile = policy.applied_transport_profile_id
        if target_profile and policy.active_transport_profile_id != target_profile:
            return (
                "rotation actuation is still pending because the active profile "
                "has not converged to the target profile"
            )
        if policy.channel_posture in {"blocked", "degraded"}:
            return (
                "rotation actuation converged, but the rollout channel remains "
                f"{policy.channel_posture} after the escalation window"
            )
        return None

    return "applied Helix actuation remains active past the escalation window"


def _format_applied_message(
    rollout: HelixRolloutState,
    *,
    canary_evidence: HelixRolloutCanaryEvidence | None,
    now: datetime,
) -> str:
    policy = rollout.policy
    canary_summary = ""
    if canary_evidence is not None:
        canary_summary = f"Canary decision: <b>{canary_evidence.decision}</b>\n"
        if canary_evidence.snapshot.average_relative_throughput_ratio is not None:
            canary_summary += (
                "Canary throughput ratio: <b>"
                f"{canary_evidence.snapshot.average_relative_throughput_ratio:.2f}"
                "</b>\n"
            )
        if (
            canary_evidence.snapshot.average_relative_open_to_first_byte_gap_ratio
            is not None
        ):
            canary_summary += (
                "Canary gap ratio: <b>"
                f"{canary_evidence.snapshot.average_relative_open_to_first_byte_gap_ratio:.2f}"
                "</b>\n"
            )
        if canary_evidence.reasons:
            canary_summary += (
                "Canary reasons: "
                f"{'; '.join(canary_evidence.reasons)}\n"
            )
        if canary_evidence.evidence_gaps:
            canary_summary += (
                "Canary evidence gaps: "
                f"{'; '.join(canary_evidence.evidence_gaps)}\n"
            )
        if canary_evidence.recommended_follow_up_action is not None:
            canary_summary += (
                "Canary follow-up action: "
                f"{canary_evidence.recommended_follow_up_action}\n"
            )
        if canary_evidence.recommended_follow_up_tasks:
            canary_summary += (
                "Canary follow-up tasks: "
                f"{'; '.join(canary_evidence.recommended_follow_up_tasks)}\n"
            )
    return (
        "🚨 <b>Helix Automatic Actuation Applied</b>\n\n"
        f"Rollout: <code>{rollout.rollout_id}</code>\n"
        f"Channel: <code>{rollout.channel}</code>\n"
        f"Applied reaction: <b>{policy.applied_automatic_reaction or 'none'}</b>\n"
        f"Trigger reason: {policy.automatic_reaction_trigger_reason or 'not provided'}\n"
        f"Observed active profile: <code>{policy.active_transport_profile_id or 'unknown'}</code>\n"
        f"Applied target profile: <code>{policy.applied_transport_profile_id or 'none'}</code>\n"
        f"Channel posture: <b>{policy.channel_posture}</b>\n"
        f"Desired rollout state: <b>{rollout.desired_state}</b>\n"
        f"{canary_summary}"
        "Ops follow-up:\n"
        f"{_format_followup_tasks(rollout)}\n"
        f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
    )


def _format_escalated_message(
    rollout: HelixRolloutState,
    *,
    canary_evidence: HelixRolloutCanaryEvidence | None,
    age_seconds: int,
    reason: str,
    now: datetime,
) -> str:
    policy = rollout.policy
    canary_summary = ""
    if canary_evidence is not None:
        canary_summary = f"Canary decision: <b>{canary_evidence.decision}</b>\n"
        if canary_evidence.snapshot.average_relative_throughput_ratio is not None:
            canary_summary += (
                "Canary throughput ratio: <b>"
                f"{canary_evidence.snapshot.average_relative_throughput_ratio:.2f}"
                "</b>\n"
            )
        if (
            canary_evidence.snapshot.average_relative_open_to_first_byte_gap_ratio
            is not None
        ):
            canary_summary += (
                "Canary gap ratio: <b>"
                f"{canary_evidence.snapshot.average_relative_open_to_first_byte_gap_ratio:.2f}"
                "</b>\n"
            )
        if canary_evidence.recommended_follow_up_action is not None:
            canary_summary += (
                "Canary follow-up action: "
                f"{canary_evidence.recommended_follow_up_action}\n"
            )
        if canary_evidence.recommended_follow_up_tasks:
            canary_summary += (
                "Canary follow-up tasks: "
                f"{'; '.join(canary_evidence.recommended_follow_up_tasks)}\n"
            )
    return (
        "🚨 <b>Helix Actuation Escalated</b>\n\n"
        f"Rollout: <code>{rollout.rollout_id}</code>\n"
        f"Channel: <code>{rollout.channel}</code>\n"
        f"Applied reaction: <b>{policy.applied_automatic_reaction or 'none'}</b>\n"
        f"Observed active profile: <code>{policy.active_transport_profile_id or 'unknown'}</code>\n"
        f"Applied target profile: <code>{policy.applied_transport_profile_id or 'none'}</code>\n"
        f"Actuation age: <b>{age_seconds}s</b>\n"
        f"Reason: {reason}\n"
        f"{canary_summary}"
        "Ops follow-up:\n"
        f"{_format_followup_tasks(rollout)}\n"
        f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
    )


def _format_resolved_message(
    rollout: HelixRolloutState,
    *,
    previous_reaction: str,
    now: datetime,
) -> str:
    return (
        "✅ <b>Helix Actuation Cleared</b>\n\n"
        f"Rollout: <code>{rollout.rollout_id}</code>\n"
        f"Channel: <code>{rollout.channel}</code>\n"
        f"Cleared reaction: <b>{previous_reaction}</b>\n"
        f"Recovered at: {now.strftime('%Y-%m-%d %H:%M UTC')}"
    )


@broker.task(task_name="audit_helix_actuations", queue="monitoring")
async def audit_helix_actuations() -> dict:
    """Track lifecycle of applied Helix actuation states and escalate stale ones."""
    settings = get_settings()
    if not settings.helix_enabled:
        return {"skipped": True, "reason": "helix_disabled"}

    redis = get_redis_client()
    cache = CacheService(redis)
    alerts_sent = 0
    active_rollouts = 0
    newly_applied = 0
    escalated = 0
    recovered = 0
    now = datetime.now(UTC)

    try:
        async with (
            HelixService() as helix,
            TelegramClient() as telegram,
        ):
            rollout_states = await helix.list_active_rollout_states()

            for rollout in rollout_states:
                state_key = HELIX_ACTUATION_AUDIT_KEY.format(
                    rollout_id=rollout.rollout_id
                )
                previous_state = await cache.get(state_key) or {}
                previous_active = bool(previous_state.get("active", False))
                previous_signature = previous_state.get("signature", "")
                previous_escalated = bool(previous_state.get("escalated", False))
                previous_reason = previous_state.get("escalation_reason")
                previous_reaction = previous_state.get("reaction")

                policy = rollout.policy
                reaction = policy.applied_automatic_reaction
                signature = (
                    f"{reaction}|{policy.applied_transport_profile_id or ''}"
                    if reaction
                    else ""
                )
                age_seconds = None
                if policy.automatic_reaction_updated_at is not None:
                    age_seconds = max(
                        int(
                            (now - policy.automatic_reaction_updated_at).total_seconds()
                        ),
                        0,
                    )

                escalation_reason = None
                canary_evidence = None
                if reaction is not None:
                    canary_evidence = await helix.get_rollout_canary_evidence(
                        rollout.rollout_id
                    )
                if (
                    reaction is not None
                    and age_seconds is not None
                    and age_seconds >= settings.helix_actuation_escalation_seconds
                ):
                    escalation_reason = _describe_escalation(
                        rollout,
                        age_seconds=age_seconds,
                    )

                if reaction is not None:
                    active_rollouts += 1
                    if not previous_active or previous_signature != signature:
                        await telegram.send_admin_alert(
                            _format_applied_message(
                                rollout,
                                canary_evidence=canary_evidence,
                                now=now,
                            ),
                            severity="critical",
                        )
                        alerts_sent += 1
                        newly_applied += 1
                    elif escalation_reason is not None and (
                        not previous_escalated or previous_reason != escalation_reason
                    ):
                        await telegram.send_admin_alert(
                            _format_escalated_message(
                                rollout,
                                canary_evidence=canary_evidence,
                                age_seconds=age_seconds or 0,
                                reason=escalation_reason,
                                now=now,
                            ),
                            severity="critical",
                        )
                        alerts_sent += 1
                        escalated += 1
                elif previous_active and previous_reaction:
                    await telegram.send_admin_alert(
                        _format_resolved_message(
                            rollout,
                            previous_reaction=previous_reaction,
                            now=now,
                        ),
                        severity="resolved",
                    )
                    alerts_sent += 1
                    recovered += 1

                await cache.set(
                    state_key,
                    {
                        "active": reaction is not None,
                        "signature": signature,
                        "reaction": reaction,
                        "target_profile_id": policy.applied_transport_profile_id,
                        "observed_active_profile_id": policy.active_transport_profile_id,
                        "automatic_reaction_updated_at": (
                            policy.automatic_reaction_updated_at.isoformat()
                            if policy.automatic_reaction_updated_at is not None
                            else None
                        ),
                        "age_seconds": age_seconds,
                        "escalated": escalation_reason is not None,
                        "escalation_reason": escalation_reason,
                        "updated_at": int(now.timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

        logger.info(
            "helix_actuation_audit_complete",
            rollouts_checked=len(rollout_states),
            active_rollouts=active_rollouts,
            newly_applied=newly_applied,
            escalated=escalated,
            recovered=recovered,
            alerts_sent=alerts_sent,
        )
        return {
            "skipped": False,
            "rollouts_checked": len(rollout_states),
            "active_rollouts": active_rollouts,
            "newly_applied": newly_applied,
            "escalated": escalated,
            "recovered": recovered,
            "alerts_sent": alerts_sent,
        }
    finally:
        await redis.aclose()
