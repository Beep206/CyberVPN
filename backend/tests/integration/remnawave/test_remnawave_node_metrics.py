from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_stage1_remnawave_node_metric_rules_cover_2_8_cpu_and_traffic_families() -> None:
    rules = (REPO_ROOT / "infra/prometheus/rules/stage1_dashboard_recording_rules.yml").read_text()

    required_fragments = (
        "remnawave_node_cpu_load_avg_1m",
        "remnawave_node_cpu_load_avg_5m",
        "remnawave_node_cpu_load_avg_15m",
        "remnawave_node_cpu_count",
        'clamp_min(max by (node_uuid) (remnawave_node_cpu_count{job="remnawave"}), 1)',
        "remnawave_node_status",
        "remnawave_node_online_users",
        "remnawave_node_network_rx_bytes_per_sec",
        "remnawave_node_network_tx_bytes_per_sec",
        "stage1:remnawave_node_cpu_load_1m:normalized",
        "stage1:remnawave_node_cpu_load_5m:normalized",
        "stage1:remnawave_node_cpu_load_15m:normalized",
        "stage1:remnawave_xhttp_capable_nodes:current",
        "stage1:remnawave_premium_smart_ru_xhttp_policy_nodes:current",
        "xhttp|XHTTP",
    )

    for fragment in required_fragments:
        assert fragment in rules
    assert "xhttp|XHTTP|CYBERVPN_PREMIUM_SMART_RU" not in rules

    parsed = yaml.safe_load(rules)
    per_node_records = {
        "stage1:remnawave_node_cpu_load_1m:current",
        "stage1:remnawave_node_cpu_load_5m:current",
        "stage1:remnawave_node_cpu_load_15m:current",
        "stage1:remnawave_node_cpu_count:current",
        "stage1:remnawave_node_cpu_load_1m:normalized",
        "stage1:remnawave_node_cpu_load_5m:normalized",
        "stage1:remnawave_node_cpu_load_15m:normalized",
        "stage1:remnawave_node_online_users:current",
        "stage1:remnawave_node_network_rx_bytes_per_sec:current",
        "stage1:remnawave_node_network_tx_bytes_per_sec:current",
    }
    expressions = {
        rule["record"]: rule["expr"]
        for group in parsed["groups"]
        for rule in group["rules"]
        if rule.get("record") in per_node_records
    }
    assert set(expressions) == per_node_records
    for expr in expressions.values():
        assert "or vector(0)" not in expr


def test_stage1_cpu_alert_uses_normalized_rules_before_absolute_degraded_fallback() -> None:
    alerts = (REPO_ROOT / "infra/prometheus/rules/stage1_alerts.yml").read_text()

    assert 'max({__name__=~"stage1:remnawave_node_cpu_load_(1m|5m|15m):normalized"} > 0)' in alerts
    assert 'max({__name__=~"stage1:remnawave_node_cpu_load_(1m|5m|15m):current"})' in alerts
    assert "falls back to the absolute load average" in alerts


def test_stage1_remnawave_dashboard_has_required_identity_and_panels() -> None:
    dashboard = json.loads((REPO_ROOT / "infra/grafana/dashboards/remnawave-node-metrics-dashboard.json").read_text())

    assert dashboard["title"] == "CyberVPN / Remnawave Nodes"
    assert dashboard["uid"] == "remnawave-node-metrics"
    panel_titles = {panel["title"] for panel in dashboard["panels"]}
    assert {
        "Remnawave node CPU load normalized",
        "Healthy nodes",
        "Node metrics series",
        "XHTTP tagged and policy nodes",
        "Online users by node",
        "Node network throughput",
        "Premium Smart RU nodes",
        "Node CPU cores",
        "Node identity and versions",
    } <= panel_titles
