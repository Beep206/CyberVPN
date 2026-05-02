from datetime import UTC, datetime

from src.application.services.posthog_bridge import PostHogBridgeInput, build_posthog_capture_record


def _build_event(**overrides: object) -> PostHogBridgeInput:
    payload = {
        "event_key": "evt_123",
        "event_name": "order.finalized",
        "aggregate_id": "order-42",
        "occurred_at": datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
        "schema_version": 1,
        "actor_context": {"principal_id": "user-42", "principal_type": "customer"},
        "event_payload": {
            "order_id": "order-42",
            "settlement_status": "paid",
            "source": "wallet_only_commit",
        },
    }
    payload.update(overrides)
    return PostHogBridgeInput(**payload)


def test_builds_checkout_payment_captured_from_authoritative_order_finalized_event() -> None:
    capture = build_posthog_capture_record(_build_event())

    assert capture is not None
    assert capture.distinct_id == "user-42"
    assert capture.event == "checkout_payment_captured"
    assert capture.properties == {
        "$insert_id": "evt_123",
        "occurred_at": "2026-04-22T12:00:00+00:00",
        "order_id": "order-42",
        "settlement_status": "paid",
        "source_class": "nats_bridge",
        "source_event_key": "evt_123",
        "source_event_type": "order.finalized",
        "source_event_version": 1,
        "source_flow": "wallet_only_commit",
    }


def test_builds_partner_user_activated_from_authoritative_invite_redemption_event() -> None:
    capture = build_posthog_capture_record(
        _build_event(
            event_name="invite.redeemed",
            aggregate_id="invite-7",
            actor_context={"principal_id": "user-99", "principal_type": "customer"},
            event_payload={
                "entitlement_grant_id": "grant-1",
                "free_days": 14,
                "invite_code_id": "invite-7",
                "redeemer_user_id": "user-99",
                "source": "campaign",
            },
        )
    )

    assert capture is not None
    assert capture.distinct_id == "user-99"
    assert capture.event == "partner_user_activated"
    assert capture.properties == {
        "$insert_id": "evt_123",
        "entitlement_grant_id": "grant-1",
        "free_days": 14,
        "invite_code_id": "invite-7",
        "occurred_at": "2026-04-22T12:00:00+00:00",
        "source_class": "nats_bridge",
        "source_event_key": "evt_123",
        "source_event_type": "invite.redeemed",
        "source_event_version": 1,
        "source_flow": "campaign",
    }


def test_builds_subscription_activated_from_authoritative_entitlement_activation_event() -> None:
    capture = build_posthog_capture_record(
        _build_event(
            event_name="entitlement.grant.activated",
            aggregate_id="grant-9",
            actor_context={"principal_id": "admin-1", "principal_type": "admin"},
            event_payload={
                "auth_realm_id": "realm-1",
                "customer_account_id": "user-42",
                "entitlement_grant_id": "grant-9",
                "grant_status": "active",
                "service_identity_id": "svc-3",
                "source_type": "order",
            },
        )
    )

    assert capture is not None
    assert capture.distinct_id == "user-42"
    assert capture.event == "subscription_activated"
    assert capture.properties == {
        "$insert_id": "evt_123",
        "entitlement_grant_id": "grant-9",
        "grant_status": "active",
        "occurred_at": "2026-04-22T12:00:00+00:00",
        "source_class": "nats_bridge",
        "source_event_key": "evt_123",
        "source_event_type": "entitlement.grant.activated",
        "source_event_version": 1,
        "source_type": "order",
    }


def test_returns_none_for_unsupported_source_events() -> None:
    assert build_posthog_capture_record(_build_event(event_name="reporting.mart.refreshed")) is None


def test_returns_none_when_distinct_id_cannot_be_resolved() -> None:
    assert build_posthog_capture_record(_build_event(actor_context={"principal_type": "customer"})) is None
