import pytest
from prometheus_client import REGISTRY, generate_latest

from src.application.services.config_service import (
    MANDATORY_CABINET_ALLOWED_PREFIXES,
    MANDATORY_OPERATIONAL_PATH_PREFIXES,
    MANDATORY_PUBLIC_ALLOWED_PREFIXES,
    ConfigService,
    CustomerSiteRuntimeConfig,
)
from src.application.services.customer_site_policy import CustomerSiteRuntimePolicy


class StaticConfigRepository:
    def __init__(self, value: dict) -> None:
        self.value = value

    async def get_value(self, _key: str, _default: dict) -> dict:
        return self.value


@pytest.mark.asyncio
async def test_customer_site_runtime_config_normalizes_v62_paths_and_action() -> None:
    raw_prefixes = [
        "/dashboard",
        "",
        "//evil.com",
        "relative",
        "/settings",
        *[f"/extra-{index}" for index in range(150)],
    ]
    config = await ConfigService(
        StaticConfigRepository(
            {
                "mode": "cabinet_only",
                "version": 2,
                "cabinet_destination_path": "//evil.com",
                "allowed_path_prefixes": ["/login", "//evil.com", ""],
                "cabinet_allowed_prefixes": raw_prefixes,
                "cabinet_marketing_route_action": "unexpected",
                "public_marketing_destination_path": "relative",
                "legal_path_prefixes": ["/privacy", "//evil.com"],
                "operational_path_prefixes": ["/status", ""],
            }
        )
    ).get_customer_site_runtime_config()

    assert config.mode == "cabinet_only"
    assert config.version == 2
    assert config.cabinet_destination_path == "/dashboard"
    assert config.allowed_path_prefixes == (*MANDATORY_PUBLIC_ALLOWED_PREFIXES, "/login")
    assert config.cabinet_allowed_prefixes[: len(MANDATORY_CABINET_ALLOWED_PREFIXES)] == (
        *MANDATORY_CABINET_ALLOWED_PREFIXES,
    )
    assert "/settings" in config.cabinet_allowed_prefixes
    assert len(config.cabinet_allowed_prefixes) == 100
    assert "//evil.com" not in config.cabinet_allowed_prefixes
    assert config.cabinet_marketing_route_action == "redirect_public"
    assert config.public_marketing_destination_path == "/"
    assert config.legal_path_prefixes == ("/privacy",)
    assert config.operational_path_prefixes == (*MANDATORY_OPERATIONAL_PATH_PREFIXES, "/status")


def test_cabinet_only_redirects_public_marketing_path_to_cabinet_host() -> None:
    policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            public_hosts=("cyber-vpn.net",),
            cabinet_hosts=("my.cyber-vpn.net",),
            cabinet_destination_path="/dashboard",
        )
    )

    decision = policy.evaluate(host="cyber-vpn.net", path="/features")

    assert decision.action == "redirect"
    assert decision.reason == "cabinet_only_marketing_gate"
    assert decision.target_host == "my.cyber-vpn.net"
    assert decision.target_path == "/dashboard"
    assert decision.route_class == "marketing"
    assert "ref" in decision.preserve_query_keys
    assert "token" not in decision.preserve_query_keys


def test_cabinet_only_allows_referral_and_cabinet_paths_before_marketing_gate() -> None:
    policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            public_hosts=("cyber-vpn.net",),
            cabinet_hosts=("my.cyber-vpn.net",),
        )
    )

    referral_decision = policy.evaluate(host="cyber-vpn.net", path="/r/REF1234")
    cabinet_decision = policy.evaluate(host="my.cyber-vpn.net", path="/dashboard")

    assert referral_decision.action == "allow"
    assert referral_decision.reason == "cabinet_only_allowed_path"
    assert referral_decision.route_class == "marketing"
    assert cabinet_decision.action == "allow"
    assert cabinet_decision.reason == "cabinet_allowed_path"
    assert cabinet_decision.route_class == "cabinet"


def test_cabinet_only_allows_public_legal_and_cabinet_marketing_redirects_public() -> None:
    policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            public_hosts=("cyber-vpn.net",),
            cabinet_hosts=("my.cyber-vpn.net",),
            public_marketing_destination_path="/",
        )
    )

    legal_decision = policy.evaluate(host="cyber-vpn.net", path="/privacy")
    marketing_decision = policy.evaluate(host="my.cyber-vpn.net", path="/pricing")

    assert legal_decision.action == "allow"
    assert legal_decision.reason == "cabinet_only_public_safe_path"
    assert legal_decision.route_class == "legal"
    assert marketing_decision.action == "redirect"
    assert marketing_decision.reason == "cabinet_marketing_redirect_public"
    assert marketing_decision.target_host == "cyber-vpn.net"
    assert marketing_decision.target_path == "/"
    assert marketing_decision.route_class == "marketing"


def test_cabinet_only_cabinet_marketing_action_can_allow_or_not_found() -> None:
    allow_policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            cabinet_hosts=("my.cyber-vpn.net",),
            cabinet_marketing_route_action="allow",
        )
    )
    not_found_policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            cabinet_hosts=("my.cyber-vpn.net",),
            cabinet_marketing_route_action="not_found",
        )
    )

    allow_decision = allow_policy.evaluate(host="my.cyber-vpn.net", path="/pricing")
    not_found_decision = not_found_policy.evaluate(host="my.cyber-vpn.net", path="/pricing")

    assert allow_decision.action == "allow"
    assert allow_decision.reason == "cabinet_marketing_allowed"
    assert not_found_decision.action == "not_found"
    assert not_found_decision.reason == "cabinet_marketing_not_found"


def test_cabinet_only_prefix_matching_uses_path_segments() -> None:
    policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            public_hosts=("cyber-vpn.net",),
            cabinet_hosts=("my.cyber-vpn.net",),
            allowed_path_prefixes=("/login",),
        )
    )

    login_decision = policy.evaluate(host="cyber-vpn.net", path="/login/reset")
    lookalike_decision = policy.evaluate(host="cyber-vpn.net", path="/login-evil")

    assert login_decision.action == "allow"
    assert lookalike_decision.action == "redirect"


def test_customer_site_policy_maintenance_allows_operational_paths_only() -> None:
    policy = CustomerSiteRuntimePolicy(CustomerSiteRuntimeConfig(mode="maintenance"))

    status_decision = policy.evaluate(host="my.cyber-vpn.net", path="/status")
    dashboard_decision = policy.evaluate(host="my.cyber-vpn.net", path="/dashboard")

    assert status_decision.action == "allow"
    assert status_decision.reason == "maintenance_safe_route"
    assert status_decision.route_class == "operational"
    assert dashboard_decision.action == "maintenance"
    assert dashboard_decision.reason == "customer_site_maintenance"
    assert dashboard_decision.route_class == "cabinet"


def test_customer_site_policy_emits_v62_decision_metric() -> None:
    policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            public_hosts=("cyber-vpn.net",),
            cabinet_hosts=("my.cyber-vpn.net",),
        )
    )

    policy.evaluate(host="cyber-vpn.net", path="/pricing")

    metric_payload = generate_latest(REGISTRY).decode()
    assert "customer_site_policy_decisions_total" in metric_payload
    assert 'mode="cabinet_only"' in metric_payload
    assert 'action="redirect"' in metric_payload
    assert 'route_class="marketing"' in metric_payload
    assert 'reason="cabinet_only_marketing_gate"' in metric_payload
