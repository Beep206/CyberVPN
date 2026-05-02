import json
from pathlib import Path

import yaml

REQUIRED_RECORDING_RULES = {
    "customer_growth:reporting_governance_gap_subscriptions",
    "customer_growth:reporting_recipient_domain_blocked_subscriptions",
    "customer_growth:reporting_governance_followup_last_success_age_seconds",
    "customer_growth:reporting_governance_followup_consecutive_failures",
    "customer_growth:reporting_governance_followup_overdue_subscriptions",
}

REQUIRED_ALERTS = {
    "CustomerGrowthReportingGovernanceCoverageGap",
    "CustomerGrowthReportingRecipientDomainBlocked",
    "CustomerGrowthReportingGovernanceFollowupStale",
    "CustomerGrowthReportingGovernanceFollowupFailing",
    "CustomerGrowthReportingGovernanceFollowupOverdue",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_rules_pack() -> dict:
    rules_path = _repo_root() / "infra/prometheus/rules/customer_growth_reporting_alerts.yml"
    return yaml.safe_load(rules_path.read_text(encoding="utf-8"))


def _load_runbook() -> str:
    runbook_path = _repo_root() / "docs/runbooks/CUSTOMER_GROWTH_REPORTING_RUNBOOK.md"
    return runbook_path.read_text(encoding="utf-8")


def _load_evidence_template() -> str:
    template_path = (
        _repo_root()
        / "docs/evidence/customer-growth/templates/customer-growth-reporting-governance-evidence-template.md"
    )
    return template_path.read_text(encoding="utf-8")


def _load_handoff() -> str:
    handoff_path = (
        _repo_root()
        / "docs/runbooks/CUSTOMER_GROWTH_REPORTING_GOVERNANCE_GITHUB_PROTECTION_HANDOFF.md"
    )
    return handoff_path.read_text(encoding="utf-8")


def _load_staging_runbook() -> str:
    runbook_path = (
        _repo_root()
        / "docs/runbooks/CUSTOMER_GROWTH_REPORTING_GOVERNANCE_STAGING_ROLLOUT_RUNBOOK.md"
    )
    return runbook_path.read_text(encoding="utf-8")


def _load_package_json() -> dict:
    package_path = _repo_root() / "package.json"
    return json.loads(package_path.read_text(encoding="utf-8"))


def _load_ruleset_payload() -> dict:
    ruleset_path = (
        _repo_root()
        / ".github/rulesets/customer-growth-reporting-governance-main-gate.disabled.json"
    )
    return json.loads(ruleset_path.read_text(encoding="utf-8"))


def _rules_by_group(rules_pack: dict, group_name: str) -> list[dict]:
    for group in rules_pack["groups"]:
        if group["name"] == group_name:
            return group["rules"]
    raise AssertionError(f"Prometheus group '{group_name}' not found.")


def test_growth_reporting_governance_rule_pack_contains_required_recording_rules_and_alerts() -> None:
    rules_pack = _load_rules_pack()
    recording_rules = {
        rule["record"]
        for rule in _rules_by_group(rules_pack, "customer_growth_reporting_recording_rules")
        if "record" in rule
    }
    alert_rules = {
        rule["alert"]
        for rule in _rules_by_group(rules_pack, "customer_growth_reporting_alerts")
        if "alert" in rule
    }

    assert not (REQUIRED_RECORDING_RULES - recording_rules)
    assert not (REQUIRED_ALERTS - alert_rules)


def test_growth_reporting_governance_alerts_have_required_annotations() -> None:
    rules_pack = _load_rules_pack()
    alert_rules = {
        rule["alert"]: rule
        for rule in _rules_by_group(rules_pack, "customer_growth_reporting_alerts")
        if "alert" in rule
    }

    for alert_name in REQUIRED_ALERTS:
        rule = alert_rules[alert_name]
        annotations = rule.get("annotations", {})
        labels = rule.get("labels", {})

        assert labels.get("severity") == "warning"
        assert labels.get("service") == "customer-growth"
        assert labels.get("component") == "growth-reporting-governance"
        assert annotations.get("summary")
        assert annotations.get("description")
        assert annotations.get("runbook_path") == "docs/runbooks/CUSTOMER_GROWTH_REPORTING_RUNBOOK.md"
        assert annotations.get("runbook_url", "").endswith(
            "/docs/runbooks/CUSTOMER_GROWTH_REPORTING_RUNBOOK.md"
        )


def test_growth_reporting_governance_runbook_evidence_handoff_and_gate_assets_exist() -> None:
    repo_root = _repo_root()
    runbook = _load_runbook()
    staging_runbook = _load_staging_runbook()
    evidence_template = _load_evidence_template()
    handoff = _load_handoff()
    package_json = _load_package_json()
    ruleset_payload = _load_ruleset_payload()

    for required_term in (
        "CustomerGrowthReportingGovernanceCoverageGap",
        "CustomerGrowthReportingRecipientDomainBlocked",
        "customer_growth:reporting_governance_gap_subscriptions",
        "customer_growth:reporting_recipient_domain_blocked_subscriptions",
        "customer_growth:reporting_governance_followup_last_success_age_seconds",
        "customer_growth:reporting_governance_followup_consecutive_failures",
        "customer_growth:reporting_governance_followup_overdue_subscriptions",
        "/api/v1/admin/growth-reporting/governance",
        "/api/v1/admin/growth-reporting/governance/export",
        "npm run conformance:customer-growth-reporting-governance",
        "npm run evidence:customer-growth-reporting-governance:init",
    ):
        assert required_term in runbook

    for required_term in (
        "Customer Growth Reporting Governance Evidence",
        "GRG-001",
        "GRG-004",
        "All Customer Growth Reporting Governance Checks Passed",
        "Gate Readiness Artifact",
        "./approvals/gate-readiness.json",
    ):
        assert required_term in evidence_template

    for required_term in (
        "All Customer Growth Reporting Governance Checks Passed",
        "customer-growth-reporting-governance-main-gate",
        ".github/rulesets/customer-growth-reporting-governance-main-gate.disabled.json",
        "scripts/sync-customer-growth-reporting-governance-ruleset.sh",
        "Customer Growth Reporting Governance Staging Smoke",
        "scripts/assess-customer-growth-reporting-governance-gate-readiness.sh",
        "approvals/gate-readiness.json",
    ):
        assert required_term in handoff

    for required_term in (
        "npm run staging:customer-growth-reporting-governance:smoke",
        "npm run staging:customer-growth-reporting-governance:assess",
        "GRG-001",
        "GRG-004",
        "All Customer Growth Reporting Governance Checks Passed",
        "Customer Growth Reporting Governance Staging Smoke",
        "approvals/gate-readiness.json",
    ):
        assert required_term in staging_runbook

    scripts = package_json["scripts"]
    assert (
        scripts["conformance:customer-growth-reporting-governance"]
        == "bash ./scripts/run-customer-growth-reporting-governance-conformance.sh"
    )
    assert (
        scripts["conformance:customer-growth-reporting-governance:backend"]
        == "bash ./scripts/run-customer-growth-reporting-governance-conformance.sh --backend"
    )
    assert (
        scripts["conformance:customer-growth-reporting-governance:admin"]
        == "bash ./scripts/run-customer-growth-reporting-governance-conformance.sh --admin"
    )
    assert (
        scripts["conformance:customer-growth-reporting-governance:assets"]
        == "bash ./scripts/run-customer-growth-reporting-governance-conformance.sh --assets"
    )
    assert (
        scripts["evidence:customer-growth-reporting-governance:init"]
        == "bash ./scripts/bootstrap-customer-growth-reporting-governance-evidence.sh"
    )
    assert (
        scripts["staging:customer-growth-reporting-governance:assess"]
        == "bash ./scripts/assess-customer-growth-reporting-governance-gate-readiness.sh"
    )
    assert (
        scripts["staging:customer-growth-reporting-governance:smoke"]
        == "bash ./scripts/run-customer-growth-reporting-governance-staging-smoke.sh"
    )

    assert ruleset_payload["name"] == "customer-growth-reporting-governance-main-gate"
    assert ruleset_payload["enforcement"] == "disabled"
    required_checks = ruleset_payload["rules"][0]["parameters"]["required_status_checks"]
    assert required_checks == [{"context": "All Customer Growth Reporting Governance Checks Passed"}]

    assert (repo_root / "scripts/run-customer-growth-reporting-governance-conformance.sh").exists()
    assert (repo_root / "scripts/bootstrap-customer-growth-reporting-governance-evidence.sh").exists()
    assert (
        repo_root / "scripts/assess-customer-growth-reporting-governance-gate-readiness.sh"
    ).exists()
    assert (repo_root / "scripts/run-customer-growth-reporting-governance-staging-smoke.sh").exists()
    assert (repo_root / "scripts/sync-customer-growth-reporting-governance-ruleset.sh").exists()
    assert (
        repo_root / ".github/workflows/customer-growth-reporting-governance-conformance.yml"
    ).exists()
    assert (
        repo_root / ".github/workflows/customer-growth-reporting-governance-staging-smoke.yml"
    ).exists()
    assert (
        repo_root / ".github/rulesets/customer-growth-reporting-governance-main-gate.disabled.json"
    ).exists()
    assert (
        repo_root / "docs/runbooks/CUSTOMER_GROWTH_REPORTING_GOVERNANCE_STAGING_ROLLOUT_RUNBOOK.md"
    ).exists()
