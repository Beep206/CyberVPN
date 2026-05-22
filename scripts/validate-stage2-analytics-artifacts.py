#!/usr/bin/env python3
"""Validate Stage 2 analytics, dashboard, alerting, and quality gate assets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_DIR = ROOT / "infra" / "grafana" / "dashboards"
RULES_PATH = ROOT / "infra" / "prometheus" / "rules" / "stage2_analytics_alerts.yml"
PROMETHEUS_CONFIG_PATH = ROOT / "infra" / "prometheus" / "prometheus.yml"
TARGETS_PATH = ROOT / "infra" / "prometheus" / "targets" / "stage2-public-endpoints.json"
SUBSCRIPTION_TARGETS_PATH = ROOT / "infra" / "prometheus" / "targets" / "stage2-subscription-route.json"
VPN_NODE_TARGETS_PATH = ROOT / "infra" / "prometheus" / "targets" / "stage2-vpn-node-tcp.json"
BLACKBOX_CONFIG_PATH = ROOT / "infra" / "blackbox" / "blackbox.yml"
COMPOSE_PATH = ROOT / "infra" / "docker-compose.yml"
PLAN_PATH = ROOT / "docs" / "plans" / "2026-05-10-cybervpn-stage2-analytics-quality-gates-plan.md"
RUNBOOK_PATH = ROOT / "docs" / "runbooks" / "STAGE2_ANALYTICS_AND_REPORTING.md"

REQUIRED_DASHBOARDS = {
    "stage2-payment-reconciliation-dashboard.json": {
        "uid": "stage2-payment-reconciliation",
        "fragments": {
            "stage2:payment_success_ratio:24h",
            "stage2:paid_but_no_access:current",
            "stage2:webhook_failures:1h",
        },
    },
    "stage2-refund-renewal-dashboard.json": {
        "uid": "stage2-refund-renewal",
        "fragments": {
            "stage2:refunds:24h",
            "stage2:renewal_success_ratio:24h",
            "cybervpn_subscription_renewals_total",
        },
    },
    "stage2-subscription-expiry-dashboard.json": {
        "uid": "stage2-subscription-expiry",
        "fragments": {
            "stage2:subscriptions_expiring_24h",
            "stage2:expired_disable_failures:24h",
            "cybervpn_subscription_expiry_disable_total",
        },
    },
    "stage2-support-sla-dashboard.json": {
        "uid": "stage2-support-sla",
        "fragments": {
            "stage2:support_open_items:current",
            "stage2:support_sla_overdue:current",
            "stage2:support_first_response_p95_seconds",
        },
    },
    "stage2-status-page-dashboard.json": {
        "uid": "stage2-status-page",
        "fragments": {
            "stage2:status_public_endpoint_success_ratio:5m",
            "stage2:customer_edge_success_ratio:5m",
            "stage2:subscription_route_success_ratio:5m",
            "stage2:vpn_node_tcp_success_ratio:5m",
            "stage2:tls_cert_min_days",
            "probe_success",
        },
    },
    "stage2-product-analytics-dashboard.json": {
        "uid": "stage2-product-analytics",
        "fragments": {
            "stage2:analytics_ingestion_dropped:15m",
            "stage2:frontend_web_vitals_lcp_p75_seconds",
            "stage2:checkout_conversion_ratio:24h",
        },
    },
    "stage2-release-quality-dashboard.json": {
        "uid": "stage2-release-quality",
        "fragments": {
            "stage2:release_security_gate_failures:24h",
            "stage2:restore_drill_age_seconds",
            "stage2:sentry_frontend_errors:1h",
        },
    },
}

REQUIRED_RECORDING_RULES = {
    "stage2:payment_success_ratio:24h",
    "stage2:payment_failures:24h",
    "stage2:paid_but_no_access:current",
    "stage2:payment_reconciliation_max_age_minutes",
    "stage2:webhook_failures:1h",
    "stage2:webhook_retries:1h",
    "stage2:refunds:24h",
    "stage2:chargebacks:24h",
    "stage2:renewal_success_ratio:24h",
    "stage2:renewal_failures:24h",
    "stage2:subscriptions_expiring_24h",
    "stage2:subscriptions_expiring_72h",
    "stage2:subscriptions_expiring_7d",
    "stage2:expired_disable_failures:24h",
    "stage2:support_open_items:current",
    "stage2:support_sla_overdue:current",
    "stage2:support_first_response_p95_seconds",
    "stage2:support_resolution_p95_seconds",
    "stage2:customer_edge_success_ratio:5m",
    "stage2:home_ops_edge_success_ratio:5m",
    "stage2:subscription_route_success_ratio:5m",
    "stage2:vpn_node_tcp_success_ratio:5m",
    "stage2:status_public_endpoint_success_ratio:5m",
    "stage2:synthetic_failures:15m",
    "stage2:synthetic_slow_probes:15m",
    "stage2:tls_cert_min_days",
    "stage2:analytics_ingestion_dropped:15m",
    "stage2:frontend_web_vitals_lcp_p75_seconds",
    "stage2:frontend_web_vitals_inp_p75_seconds",
    "stage2:frontend_web_vitals_cls_p75_ratio",
    "stage2:checkout_conversion_ratio:24h",
    "stage2:release_security_gate_failures:24h",
    "stage2:sbom_age_seconds",
    "stage2:restore_drill_age_seconds",
    "stage2:sentry_frontend_errors:1h",
}

REQUIRED_ALERTS = {
    "Stage2PaymentReconciliationBacklog",
    "Stage2RefundSpike",
    "Stage2RenewalFailures",
    "Stage2SubscriptionExpiryBacklog",
    "Stage2SupportSlaBreach",
    "Stage2StatusEndpointDown",
    "Stage2CustomerEdgeProbeFailed",
    "Stage2SubscriptionRouteProbeFailed",
    "Stage2VpnNodeTcpProbeFailed",
    "Stage2HomeOpsEdgeProbeFailed",
    "Stage2TlsCertificateExpiresSoon",
    "Stage2AnalyticsIngestionDroppingEvents",
    "Stage2RestoreDrillOverdue",
    "Stage2SecurityQualityGateFailed",
    "Stage2SentryFrontendErrorsElevated",
}

REQUIRED_CI_FRAGMENTS = {
    "observability:stage2-artifacts:",
    "quality:release-comparison-report:",
    "sentry:frontend-sourcemaps:",
    "scripts/validate-stage2-analytics-artifacts.py",
    "scripts/release/generate-release-comparison-report.sh",
    "scripts/sentry/upload-frontend-sourcemaps.sh",
}


def _read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def _dashboard_query_text(dashboard: dict) -> str:
    exprs: list[str] = []
    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            if isinstance(target, dict):
                exprs.append(str(target.get("expr", "")))
    return "\n".join(exprs)


def _recording_rule_names(text: str) -> set[str]:
    return set(re.findall(r"^\s*-\s*record:\s*([^\s]+)\s*$", text, re.MULTILINE))


def _alert_names(text: str) -> set[str]:
    return set(re.findall(r"^\s*-\s*alert:\s*([A-Za-z0-9_]+)\s*$", text, re.MULTILINE))


def main() -> int:
    for filename, expected in REQUIRED_DASHBOARDS.items():
        path = DASHBOARD_DIR / filename
        dashboard = json.loads(_read(path))
        assert dashboard["uid"] == expected["uid"], f"{filename} uid mismatch"
        assert "stage2" in dashboard.get("tags", []), f"{filename} missing stage2 tag"
        assert dashboard.get("templating", {}).get("list"), f"{filename} missing templating"
        query_text = _dashboard_query_text(dashboard)
        for fragment in expected["fragments"]:
            assert fragment in query_text, f"{filename} missing query fragment {fragment!r}"

    rules_text = _read(RULES_PATH)
    missing_rules = REQUIRED_RECORDING_RULES - _recording_rule_names(rules_text)
    assert not missing_rules, f"Missing Stage 2 recording rules: {sorted(missing_rules)}"

    missing_alerts = REQUIRED_ALERTS - _alert_names(rules_text)
    assert not missing_alerts, f"Missing Stage 2 alerts: {sorted(missing_alerts)}"

    for fragment in ("stage: s2", "priority: p0", "priority: p1", "dashboard_path:", "runbook_path:"):
        assert fragment in rules_text, f"Missing Stage 2 alert fragment {fragment!r}"

    prometheus_config = _read(PROMETHEUS_CONFIG_PATH)
    assert "stage2_analytics_alerts.yml" in prometheus_config
    assert "stage2-public-endpoints" in prometheus_config
    assert "stage2-subscription-route" in prometheus_config
    assert "stage2-vpn-node-tcp" in prometheus_config
    assert "blackbox-exporter:9115" in prometheus_config

    targets = json.loads(_read(TARGETS_PATH))
    assert targets and targets[0].get("targets"), "Stage 2 public endpoint target list is empty"
    assert all("ozoxy.ru" not in target for item in targets for target in item.get("targets", []))
    target_text = "\n".join(target for item in targets for target in item.get("targets", []))
    for fragment in (
        "https://cyber-vpn.net/",
        "https://api.cyber-vpn.net/health",
        "https://cyber-vpn.net/ru-RU/miniapp/home",
        "https://admin.cyber-vpn.net/ru-RU/login",
        "https://gitlab.h.cyber-vpn.net/users/sign_in",
    ):
        assert fragment in target_text, f"Missing Stage 2 public endpoint target {fragment!r}"

    subscription_targets = json.loads(_read(SUBSCRIPTION_TARGETS_PATH))
    subscription_text = "\n".join(
        target for item in subscription_targets for target in item.get("targets", [])
    )
    assert "https://cyber-vpn.net/api/sub/" in subscription_text
    assert "delivery_domain_expected" in json.dumps(subscription_targets)

    vpn_targets = json.loads(_read(VPN_NODE_TARGETS_PATH))
    vpn_text = "\n".join(target for item in vpn_targets for target in item.get("targets", []))
    assert "de-1.cyber-vpn.org:443" in vpn_text
    assert "de-1.cyber-vpn.org:8443" in vpn_text

    blackbox = _read(BLACKBOX_CONFIG_PATH)
    assert "http_2xx" in blackbox
    assert "http_2xx_3xx_4xx" in blackbox
    assert "tcp_connect" in blackbox
    assert "blackbox-exporter" in _read(COMPOSE_PATH)

    _read(PLAN_PATH)
    runbook = _read(RUNBOOK_PATH)
    for fragment in (
        "Payment reconciliation",
        "Product analytics ingestion",
        "Sentry source maps",
        "Synthetic Checks",
        "Subscription route",
        "VPN node",
        "CI quality gates",
    ):
        assert fragment in runbook, f"Runbook missing section {fragment!r}"

    ci = _read(ROOT / ".gitlab-ci.yml")
    for fragment in REQUIRED_CI_FRAGMENTS:
        assert fragment in ci, f"Missing CI fragment {fragment!r}"

    print("PASS: Stage 2 analytics dashboards, rules, targets, runbooks, and CI gates are wired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
