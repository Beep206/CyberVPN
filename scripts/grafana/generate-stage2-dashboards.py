#!/usr/bin/env python3
"""Generate CyberVPN Stage 2 Grafana dashboard JSON files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT / "infra" / "grafana" / "dashboards"
DATASOURCE = {"type": "prometheus", "uid": "${datasource}"}
LOKI_DATASOURCE = {"type": "loki", "uid": "${loki_datasource}"}
RUNBOOK_URL = "https://github.com/Beep206/CyberVPN/blob/main/docs/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md"


def _target(expr: str, ref_id: str = "A", datasource: dict[str, str] | None = None) -> dict:
    return {
        "datasource": datasource or DATASOURCE,
        "editorMode": "code",
        "expr": expr,
        "legendFormat": "{{service}} {{status}} {{result}} {{instance}}",
        "range": True,
        "refId": ref_id,
    }


def _panel(
    *,
    panel_id: int,
    title: str,
    kind: str,
    expr: str,
    x: int,
    y: int,
    w: int,
    h: int,
    unit: str = "none",
    thresholds: tuple[tuple[str, float | None], ...] | None = None,
    datasource: dict[str, str] | None = None,
) -> dict:
    if thresholds is None:
        thresholds = (("green", None), ("orange", 1), ("red", 5))
    return {
        "datasource": datasource or DATASOURCE,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": color, "value": value} for color, value in thresholds],
                },
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": panel_id,
        "options": {
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": kind != "stat"},
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showPercentChange": False,
            "textMode": "auto",
        },
        "targets": [_target(expr, datasource=datasource)],
        "title": title,
        "type": kind,
    }


def stat(panel_id: int, title: str, expr: str, x: int, y: int, unit: str = "none") -> dict:
    return _panel(panel_id=panel_id, title=title, kind="stat", expr=expr, x=x, y=y, w=6, h=5, unit=unit)


def timeseries(panel_id: int, title: str, expr: str, x: int, y: int, w: int = 12, unit: str = "none") -> dict:
    return _panel(panel_id=panel_id, title=title, kind="timeseries", expr=expr, x=x, y=y, w=w, h=8, unit=unit)


def table(panel_id: int, title: str, expr: str, x: int, y: int, w: int = 24) -> dict:
    panel = _panel(panel_id=panel_id, title=title, kind="table", expr=expr, x=x, y=y, w=w, h=8)
    panel["options"] = {
        "cellHeight": "sm",
        "footer": {"countRows": False, "fields": "", "reducer": ["sum"], "show": False},
        "showHeader": True,
    }
    return panel


def logs(panel_id: int, title: str, expr: str, x: int, y: int, w: int = 24) -> dict:
    return {
        "datasource": LOKI_DATASOURCE,
        "gridPos": {"h": 8, "w": w, "x": x, "y": y},
        "id": panel_id,
        "options": {
            "dedupStrategy": "none",
            "enableLogDetails": True,
            "prettifyLogMessage": False,
            "showCommonLabels": False,
            "showLabels": False,
            "showTime": True,
            "sortOrder": "Descending",
            "wrapLogMessage": True,
        },
        "targets": [{"datasource": LOKI_DATASOURCE, "expr": expr, "refId": "A"}],
        "title": title,
        "type": "logs",
    }


def dashboard(uid: str, title: str, description: str, tags: list[str], panels: list[dict]) -> dict:
    return {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(255, 0, 0, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard",
                }
            ]
        },
        "description": description,
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [{"asDropdown": False, "icon": "external link", "includeVars": True, "keepTime": True, "targetBlank": True, "title": "Stage 2 Analytics Runbook", "type": "link", "url": RUNBOOK_URL}],
        "panels": panels,
        "refresh": "30s",
        "schemaVersion": 41,
        "style": "dark",
        "tags": ["cybervpn", "stage2", *tags],
        "templating": {
            "list": [
                {
                    "current": {"selected": False, "text": "Prometheus", "value": "prometheus"},
                    "hide": 0,
                    "includeAll": False,
                    "label": "Prometheus datasource",
                    "multi": False,
                    "name": "datasource",
                    "options": [],
                    "query": "prometheus",
                    "refresh": 1,
                    "regex": "",
                    "type": "datasource",
                },
                {
                    "current": {"selected": False, "text": "Loki", "value": "loki"},
                    "hide": 0,
                    "includeAll": False,
                    "label": "Loki datasource",
                    "multi": False,
                    "name": "loki_datasource",
                    "options": [],
                    "query": "loki",
                    "refresh": 1,
                    "regex": "",
                    "type": "datasource",
                },
                {
                    "allValue": ".*",
                    "current": {"selected": False, "text": "All", "value": "$__all"},
                    "hide": 0,
                    "includeAll": True,
                    "label": "Environment",
                    "multi": True,
                    "name": "environment",
                    "options": [],
                    "query": "prod,stage,lab",
                    "type": "custom",
                },
            ]
        },
        "time": {"from": "now-7d", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": title,
        "uid": uid,
        "version": 1,
    }


DASHBOARDS: dict[str, dict] = {
    "stage2-payment-reconciliation-dashboard.json": dashboard(
        "stage2-payment-reconciliation",
        "Stage 2 Payment Reconciliation",
        "Finance and support dashboard for paid-but-no-access, orphan payments, webhook retries, and reconciliation age.",
        ["payments", "reconciliation", "finance"],
        [
            stat(1, "Payment Success Ratio 24h", "stage2:payment_success_ratio:24h", 0, 0, "percentunit"),
            stat(2, "Payment Failures 24h", "stage2:payment_failures:24h", 6, 0),
            stat(3, "Paid-But-No-Access Current", "stage2:paid_but_no_access:current", 12, 0),
            stat(4, "Max Reconciliation Age", "stage2:payment_reconciliation_max_age_minutes", 18, 0, "m"),
            timeseries(5, "Payment Results By Status", "sum by (status, currency) (increase(payments_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "Webhook Failures And Retries", "stage2:webhook_failures:1h or stage2:webhook_retries:1h", 12, 5, 12),
            table(7, "Current Reconciliation Findings By Severity", "sum by (severity) (cybervpn_stage1_payment_reconciliation_items_current) or vector(0)", 0, 13),
            logs(8, "Payment/Reconciliation Errors", "{container=~\".*(backend|worker).*\"} |= \"payment\" |~ \"error|failed|reconcile|orphan\" ", 0, 21),
        ],
    ),
    "stage2-refund-renewal-dashboard.json": dashboard(
        "stage2-refund-renewal",
        "Stage 2 Refund And Renewal",
        "Refund, chargeback, renewal, and retention signals for Stage 2 revenue operations.",
        ["payments", "refunds", "renewals"],
        [
            stat(1, "Refunds 24h", "stage2:refunds:24h", 0, 0),
            stat(2, "Chargebacks 24h", "stage2:chargebacks:24h", 6, 0),
            stat(3, "Renewal Success Ratio 24h", "stage2:renewal_success_ratio:24h", 12, 0, "percentunit"),
            stat(4, "Renewal Failures 24h", "stage2:renewal_failures:24h", 18, 0),
            timeseries(5, "Refunds By Provider/Reason", "sum by (provider, reason) (increase(cybervpn_refunds_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "Renewals By Result", "sum by (result, plan_type) (increase(cybervpn_subscription_renewals_total[1h])) or vector(0)", 12, 5, 12),
            table(7, "Refund And Chargeback Reasons 7d", "sum by (provider, reason) (increase(cybervpn_refunds_total[7d])) or vector(0)", 0, 13),
            logs(8, "Refund/Renewal Exceptions", "{container=~\".*(backend|worker).*\"} |~ \"refund|renewal|chargeback\" |~ \"error|failed|exception\"", 0, 21),
        ],
    ),
    "stage2-subscription-expiry-dashboard.json": dashboard(
        "stage2-subscription-expiry",
        "Stage 2 Subscription Expiry",
        "Subscription expiry, grace-period, renewal risk, and access-disable visibility.",
        ["subscriptions", "expiry", "retention"],
        [
            stat(1, "Expiring 24h", "stage2:subscriptions_expiring_24h", 0, 0),
            stat(2, "Expiring 72h", "stage2:subscriptions_expiring_72h", 6, 0),
            stat(3, "Expiring 7d", "stage2:subscriptions_expiring_7d", 12, 0),
            stat(4, "Expired Disable Failures 24h", "stage2:expired_disable_failures:24h", 18, 0),
            timeseries(5, "Expiry Forecast", "stage2:subscriptions_expiring_24h or stage2:subscriptions_expiring_72h or stage2:subscriptions_expiring_7d", 0, 5, 12),
            timeseries(6, "Expiry Disable Outcomes", "sum by (result) (increase(cybervpn_subscription_expiry_disable_total[1h])) or vector(0)", 12, 5, 12),
            table(7, "Grace Period Risk By Plan", "sum by (plan_type, risk_level) (cybervpn_subscription_expiry_risk_current) or vector(0)", 0, 13),
            logs(8, "Expiry And Access Disable Logs", "{container=~\".*(backend|worker).*\"} |~ \"expiry|expired|disable|subscription\" |~ \"error|failed|blocked\"", 0, 21),
        ],
    ),
    "stage2-support-sla-dashboard.json": dashboard(
        "stage2-support-sla",
        "Stage 2 Support SLA",
        "Support backlog, first-response SLA, resolution SLA, and admin/support action visibility.",
        ["support", "sla", "operations"],
        [
            stat(1, "Open Support Items", "stage2:support_open_items:current", 0, 0),
            stat(2, "Overdue SLA Items", "stage2:support_sla_overdue:current", 6, 0),
            stat(3, "First Response P95", "stage2:support_first_response_p95_seconds", 12, 0, "s"),
            stat(4, "Resolution P95", "stage2:support_resolution_p95_seconds", 18, 0, "s"),
            timeseries(5, "Support Actions By Result", "sum by (operation, status) (increase(user_management_total[1h])) or sum by (operation, status) (increase(cybervpn_support_actions_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "SLA Breach Trend", "increase(cybervpn_support_sla_breaches_total[1h]) or vector(0)", 12, 5, 12),
            table(7, "Backlog By Priority", "sum by (priority, queue) (cybervpn_support_open_items_current) or vector(0)", 0, 13),
            logs(8, "Support/Admin Errors", "{container=~\".*backend.*\"} |~ \"support|admin|ticket|case\" |~ \"error|failed|exception\"", 0, 21),
        ],
    ),
    "stage2-status-page-dashboard.json": dashboard(
        "stage2-status-page",
        "Stage 2 Status Page Data Source",
        "Public endpoint, TLS, and status-page source signals built from Prometheus and blackbox probes.",
        ["status-page", "synthetic", "tls"],
        [
            stat(1, "Overall Probe Success 5m", "stage2:status_public_endpoint_success_ratio:5m", 0, 0, "percentunit"),
            stat(2, "Customer Edge Success 5m", "stage2:customer_edge_success_ratio:5m", 6, 0, "percentunit"),
            stat(3, "Subscription Route Success 5m", "stage2:subscription_route_success_ratio:5m", 12, 0, "percentunit"),
            stat(4, "VPN Node TCP Success 5m", "stage2:vpn_node_tcp_success_ratio:5m", 18, 0, "percentunit"),
            stat(5, "Min TLS Days", "stage2:tls_cert_min_days", 0, 5, "d"),
            stat(6, "Synthetic Failures 15m", "stage2:synthetic_failures:15m", 6, 5),
            stat(7, "Slow Public Probes 15m", "stage2:synthetic_slow_probes:15m", 12, 5),
            stat(8, "Home Ops Edge Success 5m", "stage2:home_ops_edge_success_ratio:5m", 18, 5, "percentunit"),
            timeseries(9, "Probe Success By Endpoint", "avg by (job, probe_group, instance) (probe_success{job=~\"blackbox.*|stage2-public-endpoints|stage2-subscription-route|stage2-vpn-node-tcp\"}) or vector(0)", 0, 10, 12),
            timeseries(10, "Probe Duration P95", "quantile_over_time(0.95, probe_duration_seconds{job=~\"blackbox.*|stage2-public-endpoints|stage2-subscription-route|stage2-vpn-node-tcp\"}[15m]) or vector(0)", 12, 10, 12, "s"),
            table(11, "Endpoint TLS Expiry Days", "(probe_ssl_earliest_cert_expiry{job=~\"blackbox.*|stage2-public-endpoints|stage2-subscription-route\"} - time()) / 86400", 0, 18),
            logs(12, "Caddy Edge Errors", "{container=~\".*caddy.*\"} |~ \"error|tls|upstream|502|503|504\"", 0, 26),
        ],
    ),
    "stage2-product-analytics-dashboard.json": dashboard(
        "stage2-product-analytics",
        "Stage 2 Product Analytics",
        "Low-impact product analytics ingestion, funnel, and frontend performance dashboard.",
        ["product-analytics", "frontend", "funnel"],
        [
            stat(1, "Analytics Drops 15m", "stage2:analytics_ingestion_dropped:15m", 0, 0),
            stat(2, "LCP P75", "stage2:frontend_web_vitals_lcp_p75_seconds", 6, 0, "s"),
            stat(3, "INP P75", "stage2:frontend_web_vitals_inp_p75_seconds", 12, 0, "s"),
            stat(4, "Checkout Conversion 24h", "stage2:checkout_conversion_ratio:24h", 18, 0, "percentunit"),
            timeseries(5, "Frontend Web Vitals", "stage2:frontend_web_vitals_lcp_p75_seconds or stage2:frontend_web_vitals_inp_p75_seconds or stage2:frontend_web_vitals_cls_p75_ratio", 0, 5, 12),
            timeseries(6, "Funnel Events", "sum by (event_name, result) (increase(cybervpn_product_analytics_events_total[1h])) or vector(0)", 12, 5, 12),
            table(7, "Analytics Queue By Source", "sum by (source, result) (cybervpn_product_analytics_queue_depth) or vector(0)", 0, 13),
            logs(8, "Frontend Analytics/Sentry Signals", "{container=~\".*(frontend|caddy|backend).*\"} |~ \"analytics|sentry|web-vital|frontend\" |~ \"error|drop|failed\"", 0, 21),
        ],
    ),
    "stage2-release-quality-dashboard.json": dashboard(
        "stage2-release-quality",
        "Stage 2 Release Quality Gates",
        "Security gates, SBOM, restore drill freshness, release comparison, and Sentry release health.",
        ["release", "quality", "security"],
        [
            stat(1, "Security Gate Failures 24h", "stage2:release_security_gate_failures:24h", 0, 0),
            stat(2, "SBOM Age", "stage2:sbom_age_seconds", 6, 0, "s"),
            stat(3, "Restore Drill Age", "stage2:restore_drill_age_seconds", 12, 0, "s"),
            stat(4, "Frontend Sentry Errors 1h", "stage2:sentry_frontend_errors:1h", 18, 0),
            timeseries(5, "Security Gates By Tool", "sum by (tool, result) (increase(cybervpn_ci_security_gate_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "Sentry Release Health", "sum by (project, environment) (increase(cybervpn_sentry_release_errors_total[1h])) or vector(0)", 12, 5, 12),
            table(7, "Release Comparison Drift", "sum by (artifact_type, severity) (cybervpn_release_comparison_drift_current) or vector(0)", 0, 13),
            logs(8, "CI/Security/Release Errors", "{container=~\".*(gitlab|runner).*\"} |~ \"trivy|grype|gitleaks|sbom|sentry|release\" |~ \"failed|error|critical|high\"", 0, 21),
        ],
    ),
}


def main() -> int:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    for filename, payload in DASHBOARDS.items():
        path = DASHBOARD_DIR / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
