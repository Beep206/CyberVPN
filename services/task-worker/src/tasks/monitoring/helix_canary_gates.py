"""Formal canary gate evaluation for Helix rollout channels."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

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
from src.utils.constants import HELIX_CANARY_GATE_KEY

logger = structlog.get_logger(__name__)

GateDecision = Literal["go", "watch", "no-go"]


def _severity_for_decision(decision: GateDecision) -> str:
    if decision == "no-go":
        return "critical"
    if decision == "watch":
        return "warning"
    return "resolved"


def _format_gate_message(
    rollout: HelixRolloutState,
    *,
    canary_evidence: HelixRolloutCanaryEvidence,
    now: datetime,
    transitioned_from: str | None = None,
) -> str:
    decision = canary_evidence.decision
    header = {
        "go": "✅ <b>Helix Canary Gate Cleared</b>",
        "watch": "⚠️ <b>Helix Canary Gate On Watch</b>",
        "no-go": "🚨 <b>Helix Canary No-Go</b>",
    }[decision]
    policy = rollout.policy

    body = [
        header,
        "",
        f"Rollout: <code>{rollout.rollout_id}</code>",
        f"Channel: <code>{rollout.channel}</code>",
        f"Decision: <b>{decision}</b>",
    ]

    if transitioned_from is not None:
        body.append(f"Previous decision: <b>{transitioned_from}</b>")

    body.extend(
        [
            f"Connect success: <b>{rollout.desktop.connect_success_rate:.2%}</b>",
            f"Fallback rate: <b>{rollout.desktop.fallback_rate:.2%}</b>",
            f"Continuity observations: <b>{rollout.desktop.continuity_observed_events}</b>",
            f"Continuity success: <b>{rollout.desktop.continuity_success_rate:.2%}</b>",
            f"Cross-route recovery: <b>{rollout.desktop.cross_route_recovery_rate:.2%}</b>",
            (
                "Benchmark observations: "
                f"<b>{rollout.desktop.benchmark_observed_events}</b>"
            ),
            (
                "Throughput evidence observations: "
                f"<b>{rollout.desktop.throughput_evidence_observed_events}</b>"
            ),
            (
                "Average benchmark throughput: <b>"
                f"{rollout.desktop.average_benchmark_throughput_kbps:.2f} kbps"
                "</b>"
                if rollout.desktop.average_benchmark_throughput_kbps is not None
                else "Average benchmark throughput: <b>unavailable</b>"
            ),
            (
                "Relative throughput ratio: <b>"
                f"{rollout.desktop.average_relative_throughput_ratio:.2f}"
                "</b>"
                if rollout.desktop.average_relative_throughput_ratio is not None
                else "Relative throughput ratio: <b>unavailable</b>"
            ),
            (
                "Relative open->first-byte gap ratio: <b>"
                f"{rollout.desktop.average_relative_open_to_first_byte_gap_ratio:.2f}"
                "</b>"
                if rollout.desktop.average_relative_open_to_first_byte_gap_ratio
                is not None
                else "Relative open->first-byte gap ratio: <b>unavailable</b>"
            ),
            f"Desired state: <b>{rollout.desired_state}</b>",
            f"Channel posture: <b>{policy.channel_posture}</b>",
            f"Applied reaction: <b>{policy.applied_automatic_reaction or 'none'}</b>",
            f"Applied target profile: <code>{policy.applied_transport_profile_id or 'none'}</code>",
            (
                "Gate thresholds: "
                f"<b>connect>={canary_evidence.thresholds.min_connect_success_rate:.0%}, "
                f"fallback<={canary_evidence.thresholds.max_fallback_rate:.0%}, "
                f"throughput>={canary_evidence.thresholds.min_relative_throughput_ratio:.2f}, "
                f"gap<={canary_evidence.thresholds.max_relative_open_to_first_byte_gap_ratio:.2f}</b>"
            ),
        ]
    )

    if canary_evidence.reasons:
        body.append(f"Reasons: <b>{'; '.join(canary_evidence.reasons)}</b>")
    if canary_evidence.evidence_gaps:
        body.append(
            f"Evidence gaps: <b>{'; '.join(canary_evidence.evidence_gaps)}</b>"
        )
    if canary_evidence.recommended_follow_up_action is not None:
        body.append(
            "Follow-up action: "
            f"<b>{canary_evidence.recommended_follow_up_action}</b>"
        )
    if canary_evidence.recommended_follow_up_tasks:
        body.append(
            "Follow-up tasks: "
            f"<b>{'; '.join(canary_evidence.recommended_follow_up_tasks)}</b>"
        )

    body.append(f"Observed at: {now.strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(body)


@broker.task(task_name="audit_helix_canary_gates", queue="monitoring")
async def audit_helix_canary_gates() -> dict:
    """Evaluate formal go/watch/no-go state for active Helix canary rollouts."""
    settings = get_settings()
    if not settings.helix_enabled:
        return {"skipped": True, "reason": "helix_disabled"}

    redis = get_redis_client()
    cache = CacheService(redis)
    alerts_sent = 0
    rollouts_checked = 0
    go_rollouts = 0
    watch_rollouts = 0
    no_go_rollouts = 0
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
                decision = canary_evidence.decision
                reasons = canary_evidence.reasons
                evidence_gaps = canary_evidence.evidence_gaps

                if decision == "go":
                    go_rollouts += 1
                elif decision == "watch":
                    watch_rollouts += 1
                else:
                    no_go_rollouts += 1

                state_key = HELIX_CANARY_GATE_KEY.format(
                    rollout_id=rollout.rollout_id
                )
                previous_state = await cache.get(state_key) or {}
                previous_decision = previous_state.get("decision")
                previous_signature = previous_state.get("signature", "")
                current_signature = "|".join([decision, *reasons, *evidence_gaps])

                should_alert = False
                if previous_decision != decision:
                    should_alert = True
                elif decision != "go" and previous_signature != current_signature:
                    should_alert = True

                if should_alert:
                    await telegram.send_admin_alert(
                        _format_gate_message(
                            rollout,
                            canary_evidence=canary_evidence,
                            now=now,
                            transitioned_from=previous_decision,
                        ),
                        severity=_severity_for_decision(decision),
                    )
                    alerts_sent += 1

                await cache.set(
                    state_key,
                    {
                        "decision": decision,
                        "signature": current_signature,
                        "reasons": reasons,
                        "evidence_gaps": evidence_gaps,
                        "updated_at": int(now.timestamp()),
                    },
                    ttl=settings.helix_alert_state_ttl_seconds,
                )

        logger.info(
            "helix_canary_gate_audit_complete",
            rollouts_checked=rollouts_checked,
            go_rollouts=go_rollouts,
            watch_rollouts=watch_rollouts,
            no_go_rollouts=no_go_rollouts,
            alerts_sent=alerts_sent,
        )
        return {
            "skipped": False,
            "rollouts_checked": rollouts_checked,
            "go_rollouts": go_rollouts,
            "watch_rollouts": watch_rollouts,
            "no_go_rollouts": no_go_rollouts,
            "alerts_sent": alerts_sent,
        }
    finally:
        await redis.aclose()
