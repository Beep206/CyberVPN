#!/usr/bin/env python3
"""Validate S1 metrics and dashboard assets without running Grafana."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_PATH = REPO_ROOT / "infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json"
PROMETHEUS_CONFIG_PATH = REPO_ROOT / "infra/prometheus/prometheus.yml"
RECORDING_RULES_PATH = REPO_ROOT / "infra/prometheus/rules/stage1_dashboard_recording_rules.yml"

REQUIRED_DASHBOARD_QUERIES = {
    "API Up": {"stage1:target_up", 'job="cybervpn-local-backend"'},
    "Worker Up": {"stage1:target_up", 'job="cybervpn-worker"'},
    "Bot Up": {"stage1:target_up", 'job="cybervpn-telegram-bot"'},
    "PostgreSQL Up": {"stage1:target_up", 'job="postgres"'},
    "Redis Up": {"stage1:target_up", 'job="redis"'},
    "Remnawave Up": {"stage1:target_up", 'job="remnawave"'},
    "API HTTP P95": {"stage1:api_http_p95_seconds:5m"},
    "API Error and Auth Success": {"stage1:api_http_error_ratio:5m", "stage1:auth_success_ratio:5m"},
    "Registrations 24h": {"stage1:registrations:24h"},
    "Payment Success Ratio 1h": {"stage1:payment_success_ratio:1h"},
    "Payment Events 1h": {"payments_total"},
    "Paid-But-No-Access Reconciliation": {
        "cybervpn_stage1_payment_reconciliation_items_current",
        "cybervpn_stage1_payment_reconciliation_max_age_minutes",
    },
    "Remnawave API Error Ratio": {"stage1:remnawave_external_error_ratio:5m"},
    "Remnawave Healthy Nodes": {"stage1:remnawave_healthy_nodes:current"},
    "Trial and Config Delivery": {"miniapp_config_delivery_total", "trials_activated_total"},
    "Worker Queue and Task Errors": {"cybervpn_queue_depth", "stage1:worker_task_error_ratio:5m"},
    "PostgreSQL Runtime": {"pg_stat_database_numbackends", "stage1:postgres_rollback_ratio:5m"},
    "Redis Runtime": {"stage1:redis_memory_used_bytes", "redis_rejected_connections_total"},
    "Telegram Bot Updates": {"bot_updates_total"},
    "Telegram Bot Errors and Payment Launch Blocker": {
        "stage1:telegram_bot_error_ratio:5m",
        "cybervpn_stage1_payment_reconciliation_launch_blocked",
    },
}

REQUIRED_RECORDING_RULES = {
    "stage1:target_up",
    "stage1:api_http_error_ratio:5m",
    "stage1:api_http_p95_seconds:5m",
    "stage1:auth_success_ratio:5m",
    "stage1:registrations:24h",
    "stage1:payment_success_ratio:1h",
    "stage1:payment_reconciliation_items:current",
    "stage1:payment_reconciliation_p0_items:current",
    "stage1:worker_queue_depth:current",
    "stage1:worker_task_error_ratio:5m",
    "stage1:remnawave_external_error_ratio:5m",
    "stage1:postgres_rollback_ratio:5m",
    "stage1:redis_memory_used_bytes",
    "stage1:remnawave_healthy_nodes:current",
    "stage1:telegram_bot_error_ratio:5m",
}

REQUIRED_PROMETHEUS_JOBS = {
    "cybervpn-local-backend",
    "cybervpn-worker",
    "cybervpn-telegram-bot",
    "postgres",
    "redis",
    "remnawave",
}


def _load_dashboard() -> dict:
    return json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))


def _panel_queries(dashboard: dict) -> dict[str, str]:
    panels: dict[str, str] = {}
    for panel in dashboard.get("panels", []):
        title = panel.get("title")
        if not title:
            continue
        exprs = [
            str(target.get("expr", ""))
            for target in panel.get("targets", [])
            if isinstance(target, dict)
        ]
        panels[title] = "\n".join(exprs)
    return panels


def _recording_rules() -> set[str]:
    text = RECORDING_RULES_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*-\s*record:\s*([^\s]+)\s*$", text, re.MULTILINE))


def _prometheus_jobs() -> set[str]:
    text = PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"job_name:\s*['\"]?([^'\"\n]+)['\"]?", text))


def main() -> int:
    dashboard = _load_dashboard()
    panels = _panel_queries(dashboard)

    assert dashboard["uid"] == "stage1-controlled-public-beta"
    assert dashboard["title"] == "Stage 1 Controlled Public Beta"
    assert "stage1_dashboard_recording_rules.yml" in PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8")

    for panel_title, expected_fragments in REQUIRED_DASHBOARD_QUERIES.items():
        assert panel_title in panels, f"Missing panel: {panel_title}"
        panel_query = panels[panel_title]
        for fragment in expected_fragments:
            assert fragment in panel_query, f"Panel {panel_title!r} missing query fragment {fragment!r}"

    missing_rules = REQUIRED_RECORDING_RULES - _recording_rules()
    assert not missing_rules, f"Missing recording rules: {sorted(missing_rules)}"

    missing_jobs = REQUIRED_PROMETHEUS_JOBS - _prometheus_jobs()
    assert not missing_jobs, f"Missing Prometheus jobs: {sorted(missing_jobs)}"

    print("PASS: S1 observability dashboard, recording rules and scrape jobs are wired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
