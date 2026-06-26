from src.application.services.config_service import CustomerSiteRuntimeConfig
from src.application.services.customer_site_policy import CustomerSiteRuntimePolicy


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
    assert "ref" in decision.preserve_query_keys


def test_cabinet_only_allows_referral_and_cabinet_paths_before_marketing_gate() -> None:
    policy = CustomerSiteRuntimePolicy(
        CustomerSiteRuntimeConfig(
            mode="cabinet_only",
            public_hosts=("cyber-vpn.net",),
            cabinet_hosts=("my.cyber-vpn.net",),
        )
    )

    referral_decision = policy.evaluate(host="cyber-vpn.net", path="/r/REF1234")
    cabinet_decision = policy.evaluate(host="my.cyber-vpn.net", path="/features")

    assert referral_decision.action == "allow"
    assert referral_decision.reason == "cabinet_only_allowed_path"
    assert cabinet_decision.action == "allow"
    assert cabinet_decision.reason == "cabinet_host"


def test_customer_site_policy_maintenance_mode_is_terminal() -> None:
    policy = CustomerSiteRuntimePolicy(CustomerSiteRuntimeConfig(mode="maintenance"))

    decision = policy.evaluate(host="my.cyber-vpn.net", path="/dashboard")

    assert decision.action == "maintenance"
    assert decision.reason == "customer_site_maintenance"
