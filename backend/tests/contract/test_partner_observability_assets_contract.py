import json
from pathlib import Path

import yaml

REQUIRED_RECORDING_RULES = {
    "partner_platform:auth_login_success_ratio:5m",
    "partner_platform:bootstrap_success_ratio:5m",
    "partner_platform:bootstrap_duration_seconds:p95_15m",
    "partner_platform:frontend_route_load_duration_seconds:p95_15m",
    "partner_platform:frontend_submit_failure_ratio:15m",
    "partner_platform:frontend_lcp_seconds:p75_30m",
    "partner_platform:frontend_inp_seconds:p75_30m",
    "partner_platform:payout_failures:increase15m",
    "partner_platform:outbox_lag_seconds:p95_15m",
    "partner_platform:attribution_no_owner_ratio:5m",
}

REQUIRED_ALERTS = {
    "PartnerPlatformBootstrapFailureRateCritical": "partner-platform-runtime",
    "PartnerPlatformBootstrapLatencyHigh": "partner-platform-runtime",
    "PartnerPlatformCrossRealmDeniedSpike": "partner-platform-runtime",
    "PartnerPlatformWrongHostTokenSpike": "partner-platform-runtime",
    "PartnerPlatformPayoutFailuresSpike": "partner-platform-runtime",
    "PartnerPlatformOutboxFailureRateHigh": "partner-platform-runtime",
    "PartnerPlatformOutboxLagHigh": "partner-platform-runtime",
    "PartnerPlatformAttributionNoOwnerRateHigh": "partner-platform-runtime",
    "PartnerPlatformFrontendRouteLoadLatencyHigh": "partner-platform-frontend-ux",
    "PartnerPlatformFrontendSubmitFailuresHigh": "partner-platform-frontend-ux",
    "PartnerPlatformFrontendErrorSpike": "partner-platform-frontend-ux",
    "PartnerPlatformFrontendLCPHigh": "partner-platform-frontend-ux",
    "PartnerPlatformFrontendINPHigh": "partner-platform-frontend-ux",
}

RUNTIME_DASHBOARD_PANELS = {
    "Partner Login Success Ratio (5m)": {"partner_platform:auth_login_success_ratio:5m"},
    "Bootstrap Success Ratio (5m)": {"partner_platform:bootstrap_success_ratio:5m"},
    "Application Submissions Rate (5m)": {"partner_platform:application_submissions:rate5m"},
    "Payout Failures (15m)": {"partner_platform:payout_failures:increase15m"},
    "Bootstrap and Outbox Latency": {
        "partner_platform:bootstrap_duration_seconds:p95_15m",
        "partner_platform:outbox_lag_seconds:p95_15m",
    },
    "Auth and Attribution Risk Signals": {
        "partner_platform:auth_cross_realm_denied:increase15m",
        "partner_platform:attribution_no_owner_ratio:5m",
    },
}

FRONTEND_DASHBOARD_PANELS = {
    "Route Load P95 (15m)": {"partner_platform:frontend_route_load_duration_seconds:p95_15m"},
    "Browser API P95 (15m)": {"partner_platform:frontend_api_call_duration_seconds:p95_15m"},
    "Submit Failure Ratio (15m)": {"partner_platform:frontend_submit_failure_ratio:15m"},
    "Frontend Error Rate (15m)": {"partner_platform:frontend_error_events:rate15m"},
    "LCP P75 (30m)": {"partner_platform:frontend_lcp_seconds:p75_30m"},
    "INP P75 (30m)": {"partner_platform:frontend_inp_seconds:p75_30m"},
    "CLS P75 (30m)": {"partner_platform:frontend_cls_ratio:p75_30m"},
    "TTFB P75 (30m)": {"partner_platform:frontend_ttfb_seconds:p75_30m"},
    "Web Vitals P75 Trend": {
        "partner_platform:frontend_lcp_seconds:p75_30m",
        "partner_platform:frontend_inp_seconds:p75_30m",
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_rules_pack() -> dict:
    rules_path = _repo_root() / "infra/prometheus/rules/partner_platform_alerts.yml"
    return yaml.safe_load(rules_path.read_text(encoding="utf-8"))


def _load_dashboard(name: str) -> dict:
    dashboard_path = _repo_root() / f"infra/grafana/dashboards/{name}"
    return json.loads(dashboard_path.read_text(encoding="utf-8"))


def _load_runbook() -> str:
    runbook_path = _repo_root() / "docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md"
    return runbook_path.read_text(encoding="utf-8")


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


def test_partner_observability_rule_pack_contains_required_recording_rules_and_alerts() -> None:
    rules_pack = _load_rules_pack()
    recording_rules = {
        rule["record"]
        for rule in _rules_by_group(rules_pack, "partner_platform_recording_rules")
        if "record" in rule
    }
    alert_rules = {
        rule["alert"]: rule
        for rule in _rules_by_group(rules_pack, "partner_platform_alerts")
        if "alert" in rule
    }

    missing_recording_rules = REQUIRED_RECORDING_RULES - recording_rules
    missing_alerts = set(REQUIRED_ALERTS) - set(alert_rules)

    assert not missing_recording_rules
    assert not missing_alerts


def test_partner_observability_alerts_have_required_annotations_and_dashboard_bindings() -> None:
    rules_pack = _load_rules_pack()
    alert_rules = {
        rule["alert"]: rule
        for rule in _rules_by_group(rules_pack, "partner_platform_alerts")
        if "alert" in rule
    }

    runtime_dashboard = _load_dashboard("partner-platform-runtime-dashboard.json")
    frontend_dashboard = _load_dashboard("partner-platform-frontend-ux-dashboard.json")
    dashboard_uids = {
        runtime_dashboard["uid"]: runtime_dashboard,
        frontend_dashboard["uid"]: frontend_dashboard,
    }

    for alert_name, expected_dashboard_uid in REQUIRED_ALERTS.items():
        rule = alert_rules[alert_name]
        annotations = rule.get("annotations", {})
        labels = rule.get("labels", {})

        assert labels.get("severity") in {"critical", "warning"}
        assert labels.get("service") == "partner-platform"
        assert annotations.get("summary")
        assert annotations.get("description")
        assert annotations.get("runbook_path") == "docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md"
        assert annotations.get("dashboard_uid") == expected_dashboard_uid
        assert annotations.get("dashboard_path", "").startswith(f"/d/{expected_dashboard_uid}/")

        runbook_path = _repo_root() / annotations["runbook_path"]
        assert runbook_path.exists()
        assert expected_dashboard_uid in dashboard_uids


def test_partner_observability_runtime_dashboard_contract_is_stable() -> None:
    dashboard = _load_dashboard("partner-platform-runtime-dashboard.json")
    panels = _panel_index(dashboard)

    assert dashboard["uid"] == "partner-platform-runtime"
    assert dashboard["title"] == "Partner Platform Runtime"

    for panel_title, expected_queries in RUNTIME_DASHBOARD_PANELS.items():
        assert panel_title in panels
        panel_queries = "\n".join(panels[panel_title])
        for query_fragment in expected_queries:
            assert query_fragment in panel_queries


def test_partner_observability_frontend_dashboard_contract_is_stable() -> None:
    dashboard = _load_dashboard("partner-platform-frontend-ux-dashboard.json")
    panels = _panel_index(dashboard)
    template_variables = {item.get("name") for item in dashboard.get("templating", {}).get("list", [])}

    assert dashboard["uid"] == "partner-platform-frontend-ux"
    assert dashboard["title"] == "Partner Platform Frontend UX"
    assert "surface" in template_variables

    for panel_title, expected_queries in FRONTEND_DASHBOARD_PANELS.items():
        assert panel_title in panels
        panel_queries = "\n".join(panels[panel_title])
        for query_fragment in expected_queries:
            assert query_fragment in panel_queries


def test_partner_observability_runbook_references_dashboards_alerts_and_staging_smoke() -> None:
    runbook = _load_runbook()

    for required_term in (
        "partner-platform-runtime",
        "partner-platform-frontend-ux",
        "PartnerPlatformBootstrapFailureRateCritical",
        "PartnerPlatformCrossRealmDeniedSpike",
        "PartnerPlatformFrontendLCPHigh",
        "PartnerPlatformFrontendINPHigh",
        "npm run staging:partner-observability:smoke",
    ):
        assert required_term in runbook
