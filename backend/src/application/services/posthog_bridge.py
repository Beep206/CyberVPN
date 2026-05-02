from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class PostHogBridgeInput:
    event_key: str
    event_name: str
    aggregate_id: str
    occurred_at: datetime
    schema_version: int
    actor_context: Mapping[str, Any]
    event_payload: Mapping[str, Any]


@dataclass(frozen=True)
class PostHogCaptureRecord:
    distinct_id: str
    event: str
    properties: dict[str, Any]


def build_posthog_capture_record(event: PostHogBridgeInput) -> PostHogCaptureRecord | None:
    handlers = {
        "entitlement.grant.activated": _build_subscription_activated,
        "invite.redeemed": _build_partner_user_activated,
        "order.finalized": _build_checkout_payment_captured,
    }
    handler = handlers.get(event.event_name)
    if handler is None:
        return None
    return handler(event)


def _build_checkout_payment_captured(event: PostHogBridgeInput) -> PostHogCaptureRecord | None:
    distinct_id = _coerce_str(event.actor_context.get("principal_id"))
    if distinct_id is None:
        return None

    return PostHogCaptureRecord(
        distinct_id=distinct_id,
        event="checkout_payment_captured",
        properties=_build_bridge_properties(
            event,
            {
                "order_id": _coerce_str(event.event_payload.get("order_id")) or event.aggregate_id,
                "settlement_status": _coerce_str(event.event_payload.get("settlement_status")) or "unknown",
                "source_flow": _coerce_str(event.event_payload.get("source")) or "unknown",
            },
        ),
    )


def _build_partner_user_activated(event: PostHogBridgeInput) -> PostHogCaptureRecord | None:
    distinct_id = (
        _coerce_str(event.event_payload.get("redeemer_user_id"))
        or _coerce_str(event.actor_context.get("principal_id"))
    )
    if distinct_id is None:
        return None

    return PostHogCaptureRecord(
        distinct_id=distinct_id,
        event="partner_user_activated",
        properties=_build_bridge_properties(
            event,
            {
                "entitlement_grant_id": _coerce_str(event.event_payload.get("entitlement_grant_id")) or "unknown",
                "free_days": _coerce_int(event.event_payload.get("free_days")) or 0,
                "invite_code_id": _coerce_str(event.event_payload.get("invite_code_id")) or event.aggregate_id,
                "source_flow": _coerce_str(event.event_payload.get("source")) or "unknown",
            },
        ),
    )


def _build_subscription_activated(event: PostHogBridgeInput) -> PostHogCaptureRecord | None:
    distinct_id = _coerce_str(event.event_payload.get("customer_account_id"))
    if distinct_id is None:
        return None

    return PostHogCaptureRecord(
        distinct_id=distinct_id,
        event="subscription_activated",
        properties=_build_bridge_properties(
            event,
            {
                "entitlement_grant_id": _coerce_str(event.event_payload.get("entitlement_grant_id")) or event.aggregate_id,
                "grant_status": _coerce_str(event.event_payload.get("grant_status")) or "unknown",
                "source_type": _coerce_str(event.event_payload.get("source_type")) or "unknown",
            },
        ),
    )


def _build_bridge_properties(
    event: PostHogBridgeInput,
    event_specific: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "$insert_id": event.event_key,
        "occurred_at": event.occurred_at.isoformat(),
        "source_class": "nats_bridge",
        "source_event_key": event.event_key,
        "source_event_type": event.event_name,
        "source_event_version": event.schema_version,
        **event_specific,
    }


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
