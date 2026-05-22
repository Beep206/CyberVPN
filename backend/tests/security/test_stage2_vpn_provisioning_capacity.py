"""S2-STAGE-08 VPN provisioning, protocol and capacity checks."""

from __future__ import annotations

from src.infrastructure.remnawave.stage1_ru_bundle import STAGE1_RU_BUNDLE_TEMPLATE_NAME
from src.presentation.api.shared.stage2_vpn_provisioning_capacity import (
    S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE,
    S2_REQUIRED_NODE_TRANSPORT_PORTS,
    S2_SUBSCRIPTION_PUBLIC_HOST,
    S2RuBundleDecision,
    S2VpnDeliveryMethod,
    S2VpnNodeEvidence,
    S2VpnReadinessState,
    S2VpnSubscriptionDeliverySnapshot,
    build_s2_support_reprovisioning_steps,
    evaluate_s2_node_capacity,
    evaluate_s2_ru_bundle,
    evaluate_s2_subscription_delivery,
)


def test_s2_subscription_delivery_requires_org_subscription_url_and_xhttp() -> None:
    decision = evaluate_s2_subscription_delivery(
        S2VpnSubscriptionDeliverySnapshot(
            primary_config="https://cyber-vpn.org/api/sub/redacted-token",
            subscription_url="https://cyber-vpn.org/api/sub/redacted-token",
            links=(
                "vless://uuid@de-1.cyber-vpn.org:443?type=tcp&security=reality&flow=xtls-rprx-vision",
                "vless://uuid@de-1.cyber-vpn.org:8443?type=xhttp&security=reality",
            ),
        )
    )

    assert decision.readiness_state == S2VpnReadinessState.READY
    assert decision.accepted is True
    assert decision.primary_method == S2VpnDeliveryMethod.SUBSCRIPTION_URL
    assert decision.subscription_host == S2_SUBSCRIPTION_PUBLIC_HOST
    assert decision.vless_reality_raw_present is True
    assert decision.vless_reality_xhttp_present is True
    assert decision.node_hosts == ("de-1.cyber-vpn.org",)
    assert decision.issues == ()


def test_s2_subscription_delivery_blocks_raw_primary_and_net_subscription_url() -> None:
    decision = evaluate_s2_subscription_delivery(
        S2VpnSubscriptionDeliverySnapshot(
            primary_config="vless://uuid@de-1.cyber-vpn.org:443?type=tcp&security=reality",
            subscription_url="https://api.cyber-vpn.net/api/sub/raw-token",
            links=("vless://uuid@de-1.cyber-vpn.org:443?type=tcp&security=reality",),
        )
    )

    assert decision.readiness_state == S2VpnReadinessState.BLOCKED
    assert decision.primary_method == S2VpnDeliveryMethod.RAW_PROXY_URI
    assert "primary_config_must_be_subscription_url" in decision.issues
    assert "subscription_url_must_use_cyber_vpn_org" in decision.issues
    assert "missing_vless-reality-xhttp" in decision.issues


def test_s2_one_connected_node_allows_canary_but_requires_second_node_before_full_public() -> None:
    decision = evaluate_s2_node_capacity(
        (
            S2VpnNodeEvidence(
                name="prod-vpn-node-1",
                host="de-1.cyber-vpn.org",
                connected=True,
                disabled=False,
                country_code="DE",
                open_transport_ports=S2_REQUIRED_NODE_TRANSPORT_PORTS,
                node_only_runtime=True,
            ),
        )
    )

    assert decision.readiness_state == S2VpnReadinessState.READY_WITH_LIMITS
    assert decision.canary_allowed is True
    assert decision.connected_nodes == 1
    assert decision.usable_nodes == 1
    assert decision.max_public_canary_users == S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE
    assert decision.full_public_opening_allowed is False
    assert decision.second_node_required_before_full_public is True
    assert "add_second_vpn_node_before_unrestricted_public_opening" in decision.recommendations


def test_s2_node_capacity_blocks_non_node_only_or_missing_ports() -> None:
    decision = evaluate_s2_node_capacity(
        (
            S2VpnNodeEvidence(
                name="bad-node",
                host="de-1.cyber-vpn.org",
                connected=True,
                disabled=False,
                country_code="DE",
                open_transport_ports=frozenset({443}),
                node_only_runtime=False,
            ),
        )
    )

    assert decision.readiness_state == S2VpnReadinessState.BLOCKED
    assert decision.canary_allowed is False
    assert "bad-node:missing_required_transport_ports" in decision.issues
    assert "bad-node:vpn_node_must_remain_node_only" in decision.issues


def test_s2_ru_bundle_applies_only_to_russian_hidden_plans(monkeypatch) -> None:
    from src.config.settings import settings

    monkeypatch.setattr(settings, "remnawave_ru_bundle_plan_codes", "ru_start,ru_basic")

    ru_start = evaluate_s2_ru_bundle(
        plan_code="ru_start",
        template_name=STAGE1_RU_BUNDLE_TEMPLATE_NAME,
        external_squad_uuid_present=True,
    )
    global_plan = evaluate_s2_ru_bundle(
        plan_code="basic",
        template_name=None,
        external_squad_uuid_present=False,
    )
    unsafe_global = evaluate_s2_ru_bundle(
        plan_code="basic",
        template_name=STAGE1_RU_BUNDLE_TEMPLATE_NAME,
        external_squad_uuid_present=True,
    )

    assert isinstance(ru_start, S2RuBundleDecision)
    assert ru_start.allowed is True
    assert ru_start.should_apply_ru_bundle is True
    assert global_plan.allowed is True
    assert global_plan.should_apply_ru_bundle is False
    assert unsafe_global.allowed is False
    assert "non_ru_plan_must_not_use_ru_bundle" in unsafe_global.issues


def test_s2_support_reprovisioning_steps_are_secret_free() -> None:
    steps = build_s2_support_reprovisioning_steps()
    serialized = str(steps).lower()

    assert steps[0] == "check_customer_lifecycle_state"
    assert "retry_or_recreate_remnawave_user_if_authorized" in steps
    assert "raw" not in serialized
    assert "token" not in serialized
    assert "password" not in serialized
    assert "secret" not in serialized
