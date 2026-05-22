import json
import re
from pathlib import Path


REQUIRED_DASHBOARDS = {
    "stage2-payment-reconciliation-dashboard.json": "stage2-payment-reconciliation",
    "stage2-refund-renewal-dashboard.json": "stage2-refund-renewal",
    "stage2-subscription-expiry-dashboard.json": "stage2-subscription-expiry",
    "stage2-support-sla-dashboard.json": "stage2-support-sla",
    "stage2-status-page-dashboard.json": "stage2-status-page",
    "stage2-product-analytics-dashboard.json": "stage2-product-analytics",
    "stage2-release-quality-dashboard.json": "stage2-release-quality",
}

REQUIRED_RECORDING_RULES = {
    "stage2:payment_success_ratio:24h",
    "stage2:paid_but_no_access:current",
    "stage2:customer_edge_success_ratio:5m",
    "stage2:subscription_route_success_ratio:5m",
    "stage2:vpn_node_tcp_success_ratio:5m",
    "stage2:home_ops_edge_success_ratio:5m",
    "stage2:status_public_endpoint_success_ratio:5m",
    "stage2:tls_cert_min_days",
    "stage2:analytics_ingestion_dropped:15m",
    "stage2:release_security_gate_failures:24h",
}

REQUIRED_ALERTS = {
    "Stage2PaymentReconciliationBacklog",
    "Stage2StatusEndpointDown",
    "Stage2CustomerEdgeProbeFailed",
    "Stage2SubscriptionRouteProbeFailed",
    "Stage2VpnNodeTcpProbeFailed",
    "Stage2HomeOpsEdgeProbeFailed",
    "Stage2SecurityQualityGateFailed",
    "Stage2SentryFrontendErrorsElevated",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _recording_rule_names(rules_text: str) -> set[str]:
    return set(re.findall(r"^\s*-\s*record:\s*([^\s]+)\s*$", rules_text, re.MULTILINE))


def _alert_names(rules_text: str) -> set[str]:
    return set(re.findall(r"^\s*-\s*alert:\s*([A-Za-z0-9_]+)\s*$", rules_text, re.MULTILINE))


def test_stage2_dashboards_exist_and_cover_observability_surfaces() -> None:
    root = _repo_root()
    dashboard_dir = root / "infra/grafana/dashboards"

    for filename, expected_uid in REQUIRED_DASHBOARDS.items():
        dashboard = json.loads((dashboard_dir / filename).read_text(encoding="utf-8"))
        query_text = "\n".join(
            str(target.get("expr", ""))
            for panel in dashboard.get("panels", [])
            for target in panel.get("targets", [])
            if isinstance(target, dict)
        )

        assert dashboard["uid"] == expected_uid
        assert "stage2" in dashboard.get("tags", [])
        assert dashboard.get("panels")
        assert "docs/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md" in json.dumps(dashboard)

        if expected_uid == "stage2-status-page":
            for fragment in (
                "stage2:customer_edge_success_ratio:5m",
                "stage2:subscription_route_success_ratio:5m",
                "stage2:vpn_node_tcp_success_ratio:5m",
                "stage2:home_ops_edge_success_ratio:5m",
            ):
                assert fragment in query_text


def test_stage2_rules_alerts_and_prometheus_jobs_are_wired() -> None:
    root = _repo_root()
    prometheus_config = (root / "infra/prometheus/prometheus.yml").read_text(encoding="utf-8")
    rules_text = (root / "infra/prometheus/rules/stage2_analytics_alerts.yml").read_text(
        encoding="utf-8"
    )

    assert "stage2_analytics_alerts.yml" in prometheus_config
    for job_name in (
        "stage2-public-endpoints",
        "stage2-subscription-route",
        "stage2-vpn-node-tcp",
    ):
        assert f"job_name: '{job_name}'" in prometheus_config

    assert REQUIRED_RECORDING_RULES <= _recording_rule_names(rules_text)
    assert REQUIRED_ALERTS <= _alert_names(rules_text)

    for fragment in (
        "stage: s2",
        "priority: p0",
        "priority: p1",
        "dashboard_path:",
        "runbook_path:",
    ):
        assert fragment in rules_text


def test_stage2_synthetic_targets_keep_customer_route_and_org_node_roles_separate() -> None:
    root = _repo_root()
    target_dir = root / "infra/prometheus/targets"
    public_targets = json.loads(
        (target_dir / "stage2-public-endpoints.json").read_text(encoding="utf-8")
    )
    subscription_targets = json.loads(
        (target_dir / "stage2-subscription-route.json").read_text(encoding="utf-8")
    )
    vpn_targets = json.loads((target_dir / "stage2-vpn-node-tcp.json").read_text(encoding="utf-8"))

    public_target_text = "\n".join(
        target for item in public_targets for target in item.get("targets", [])
    )
    subscription_target_text = "\n".join(
        target for item in subscription_targets for target in item.get("targets", [])
    )
    vpn_target_text = "\n".join(target for item in vpn_targets for target in item.get("targets", []))

    assert "https://cyber-vpn.net/" in public_target_text
    assert "https://api.cyber-vpn.net/health" in public_target_text
    assert "https://cyber-vpn.net/ru-RU/miniapp/home" in public_target_text
    assert "https://gitlab.h.cyber-vpn.net/users/sign_in" in public_target_text
    assert "https://cyber-vpn.net/api/sub/" in subscription_target_text
    assert "de-1.cyber-vpn.org:443" in vpn_target_text
    assert "de-1.cyber-vpn.org:8443" in vpn_target_text


def test_stage2_observability_docs_and_runbooks_describe_privacy_boundaries() -> None:
    root = _repo_root()
    runbook = (root / "docs/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md").read_text(
        encoding="utf-8"
    )
    stage_doc = (
        root / "docs/cybervpn_stage2_launch_docs/10_STAGE2_OBSERVABILITY_ANALYTICS.md"
    ).read_text(encoding="utf-8")

    for fragment in (
        "subscription URL tokens",
        "Telegram Bot does not require a public health endpoint",
        "HTTP/3/QUIC must remain enabled",
        "continuous home Prometheus probe uses the Cloudflare-proxied subscription route",
        "The `.org` zone remains reserved for subscription delivery and VPN node records",
    ):
        assert fragment in runbook

    for fragment in (
        "Sensitive Logging Boundaries",
        "Product analytics must be asynchronous",
        "The `.org` zone is reserved for subscription delivery and VPN node records",
    ):
        assert fragment in stage_doc
