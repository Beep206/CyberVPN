import json
from pathlib import Path

import yaml

REQUIRED_RECORDING_RULES = {
    "customer_growth:notification_customer_recovery_requests:increase24h",
    "customer_growth:notification_support_escalations:increase24h",
    "customer_growth:notification_repairs_completed:increase24h",
    "customer_growth:notification_support_resolutions:increase24h",
    "customer_growth:notification_deliveries_recovered:increase24h",
    "customer_growth:notification_unresolved_backlog_delta:24h",
    "customer_growth:notification_recovery_ratio:24h",
}

REQUIRED_ALERTS = {
    "CustomerGrowthNotificationUnresolvedBacklogHigh": "customer-growth-notification-delivery",
    "CustomerGrowthNotificationRecoveryRatioLow": "customer-growth-notification-delivery",
}

DASHBOARD_PANELS = {
    "Support Escalations (24h)": {"customer_growth:notification_support_escalations:increase24h"},
    "Repair Completed (24h)": {"customer_growth:notification_repairs_completed:increase24h"},
    "Delivery Recovered (24h)": {"customer_growth:notification_deliveries_recovered:increase24h"},
    "Unresolved Backlog Delta (24h)": {"customer_growth:notification_unresolved_backlog_delta:24h"},
    "Recovery Ratio (24h)": {"customer_growth:notification_recovery_ratio:24h"},
    "Repair And Escalation Trends": {
        "customer_growth:notification_customer_recovery_requests:increase24h",
        "customer_growth:notification_support_escalations:increase24h",
        "customer_growth:notification_support_resolutions:increase24h",
        "customer_growth:notification_deliveries_recovered:increase24h",
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_rules_pack() -> dict:
    rules_path = _repo_root() / "infra/prometheus/rules/customer_growth_notification_alerts.yml"
    return yaml.safe_load(rules_path.read_text(encoding="utf-8"))


def _load_dashboard() -> dict:
    dashboard_path = (
        _repo_root() / "infra/grafana/dashboards/customer-growth-notification-delivery-dashboard.json"
    )
    return json.loads(dashboard_path.read_text(encoding="utf-8"))


def _load_runbook() -> str:
    runbook_path = _repo_root() / "docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_DELIVERY_RUNBOOK.md"
    return runbook_path.read_text(encoding="utf-8")


def _load_staging_runbook() -> str:
    runbook_path = _repo_root() / "docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_STAGING_ROLLOUT_RUNBOOK.md"
    return runbook_path.read_text(encoding="utf-8")


def _load_handoff() -> str:
    handoff_path = _repo_root() / "docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_GITHUB_PROTECTION_HANDOFF.md"
    return handoff_path.read_text(encoding="utf-8")


def _rules_by_group(rules_pack: dict, group_name: str) -> list[dict]:
    for group in rules_pack["groups"]:
        if group["name"] == group_name:
            return group["rules"]
    raise AssertionError(f"Prometheus group '{group_name}' not found.")


def _panel_index(dashboard: dict) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for panel in dashboard.get("panels", []):
        title = panel.get("title")
        if not title:
            continue
        exprs = [
            target["expr"]
            for target in panel.get("targets", [])
            if isinstance(target, dict) and "expr" in target
        ]
        index[title] = exprs
    return index


def test_growth_notification_rule_pack_contains_required_recording_rules_and_alerts() -> None:
    rules_pack = _load_rules_pack()
    recording_rules = {
        rule["record"]
        for rule in _rules_by_group(rules_pack, "customer_growth_notification_recording_rules")
        if "record" in rule
    }
    alert_rules = {
        rule["alert"]: rule
        for rule in _rules_by_group(rules_pack, "customer_growth_notification_alerts")
        if "alert" in rule
    }

    assert not (REQUIRED_RECORDING_RULES - recording_rules)
    assert not (set(REQUIRED_ALERTS) - set(alert_rules))


def test_growth_notification_alerts_have_required_annotations_and_dashboard_binding() -> None:
    rules_pack = _load_rules_pack()
    alert_rules = {
        rule["alert"]: rule
        for rule in _rules_by_group(rules_pack, "customer_growth_notification_alerts")
        if "alert" in rule
    }
    dashboard = _load_dashboard()

    for alert_name, expected_dashboard_uid in REQUIRED_ALERTS.items():
        rule = alert_rules[alert_name]
        annotations = rule.get("annotations", {})
        labels = rule.get("labels", {})

        assert labels.get("severity") == "warning"
        assert labels.get("service") == "customer-growth"
        assert labels.get("component") == "growth-notifications"
        assert annotations.get("summary")
        assert annotations.get("description")
        assert annotations.get("runbook_path") == "docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_DELIVERY_RUNBOOK.md"
        assert annotations.get("dashboard_uid") == expected_dashboard_uid
        assert annotations.get("dashboard_path", "").startswith(f"/d/{expected_dashboard_uid}/")
        assert dashboard["uid"] == expected_dashboard_uid


def test_growth_notification_dashboard_contract_is_stable() -> None:
    dashboard = _load_dashboard()
    panels = _panel_index(dashboard)
    template_variables = {item.get("name") for item in dashboard.get("templating", {}).get("list", [])}

    assert dashboard["uid"] == "customer-growth-notification-delivery"
    assert dashboard["title"] == "Customer Growth Notification Delivery"
    assert {"surface", "delivery_channel"} <= template_variables

    for panel_title, expected_queries in DASHBOARD_PANELS.items():
        assert panel_title in panels
        panel_queries = "\n".join(panels[panel_title])
        for query_fragment in expected_queries:
            assert query_fragment in panel_queries


def test_growth_notification_runbook_and_evidence_assets_exist() -> None:
    runbook = _load_runbook()
    staging_runbook = _load_staging_runbook()
    handoff = _load_handoff()
    repo_root = _repo_root()

    for required_term in (
        "customer-growth-notification-delivery",
        "CustomerGrowthNotificationUnresolvedBacklogHigh",
        "CustomerGrowthNotificationRecoveryRatioLow",
        "npm run conformance:customer-growth-notifications",
        "npm run evidence:customer-growth-notifications:init",
        "npm run staging:customer-growth-notifications:smoke",
    ):
        assert required_term in runbook

    for required_term in (
        "npm run staging:customer-growth-notifications:smoke",
        "GCN-REPAIR-001",
        "GCN-REPAIR-004",
        "All Customer Growth Notification Checks Passed",
    ):
        assert required_term in staging_runbook

    for required_term in (
        "All Customer Growth Notification Checks Passed",
        "customer-growth-notification-main-gate",
        ".github/rulesets/customer-growth-notification-main-gate.disabled.json",
        "scripts/sync-customer-growth-notification-ruleset.sh",
    ):
        assert required_term in handoff

    assert (repo_root / "scripts/bootstrap-customer-growth-notification-evidence.sh").exists()
    assert (repo_root / "scripts/run-customer-growth-notification-staging-smoke.sh").exists()
    assert (repo_root / "scripts/sync-customer-growth-notification-ruleset.sh").exists()
    assert (
        repo_root
        / "docs/evidence/customer-growth/templates/customer-growth-notification-rollout-evidence-template.md"
    ).exists()
    assert (repo_root / ".github/workflows/customer-growth-notification-conformance.yml").exists()
    assert (
        repo_root / ".github/rulesets/customer-growth-notification-main-gate.disabled.json"
    ).exists()
