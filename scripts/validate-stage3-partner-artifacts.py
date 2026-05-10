#!/usr/bin/env python3
"""Validate Stage 3 partner/reseller artifacts without running services."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_DIR = ROOT / "infra" / "grafana" / "dashboards"
RULES_PATH = ROOT / "infra" / "prometheus" / "rules" / "stage3_partner_reseller_alerts.yml"
TARGETS_PATH = ROOT / "infra" / "prometheus" / "targets" / "stage3-storefront-endpoints.json"
COMPOSE_PATH = ROOT / "infra" / "partner-lab" / "compose.yml"
RUNBOOK_PATH = ROOT / "docs" / "runbooks" / "PARTNER_RESELLER_STAGE3_RUNBOOK.md"
PLAN_PATH = ROOT / "docs" / "plans" / "2026-05-10-cybervpn-stage3-partner-reseller-platform-plan.md"

REQUIRED_DASHBOARDS = {
    "stage3-partner-staging-readiness-dashboard.json": {
        "uid": "stage3-partner-staging-readiness",
        "fragments": {"stage3:partner_bootstrap_success_ratio:5m", "stage3:storefront_synthetic_success_ratio:5m"},
    },
    "stage3-partner-attribution-storefront-dashboard.json": {
        "uid": "stage3-partner-attribution-storefront",
        "fragments": {"stage3:partner_attribution_no_owner_ratio:5m", "stage3:partner_touchpoint_rejects:1h"},
    },
    "stage3-partner-settlement-payout-dashboard.json": {
        "uid": "stage3-partner-settlement-payout",
        "fragments": {"stage3:partner_commission_ledger_mismatches:24h", "stage3:partner_settlement_dry_run_failures:24h"},
    },
    "stage3-partner-support-audit-risk-dashboard.json": {
        "uid": "stage3-partner-support-audit-risk",
        "fragments": {"stage3:partner_audit_log_failures:1h", "stage3:partner_antifraud_flags:24h"},
    },
}

REQUIRED_RECORDING_RULES = {
    "stage3:partner_bootstrap_success_ratio:5m",
    "stage3:partner_auth_denials:15m",
    "stage3:partner_frontend_route_p95_seconds",
    "stage3:partner_frontend_api_p95_seconds",
    "stage3:partner_frontend_error_events:15m",
    "stage3:partner_attribution_no_owner_ratio:5m",
    "stage3:partner_touchpoint_rejects:1h",
    "stage3:partner_referral_reward_reversals:24h",
    "stage3:partner_statement_closes:1h",
    "stage3:partner_payout_failures:15m",
    "stage3:partner_commission_ledger_mismatches:24h",
    "stage3:partner_settlement_dry_run_failures:24h",
    "stage3:partner_payout_simulation_failures:24h",
    "stage3:partner_cases_created:24h",
    "stage3:partner_risk_reviews_open",
    "stage3:partner_audit_log_failures:1h",
    "stage3:partner_antifraud_flags:24h",
    "stage3:partner_webhook_receiver_failures:15m",
    "stage3:storefront_synthetic_success_ratio:5m",
    "stage3:storefront_synthetic_failures:15m",
}

REQUIRED_ALERTS = {
    "Stage3PartnerBootstrapFailureRate",
    "Stage3PartnerFrontendErrors",
    "Stage3PartnerAttributionNoOwnerHigh",
    "Stage3PartnerPayoutFailure",
    "Stage3PartnerCommissionLedgerMismatch",
    "Stage3PartnerSettlementDryRunFailed",
    "Stage3PartnerRiskReviewBacklog",
    "Stage3PartnerAuditLogFailure",
    "Stage3PartnerWebhookReceiverFailures",
}

REQUIRED_SCRIPTS = {
    "scripts/partner/run-webhook-test-receiver.py",
    "scripts/partner/redact-stage3-import.py",
    "scripts/partner/generate-stage3-sandbox-reports.sh",
    "scripts/partner/check-storefront-synthetic-targets.sh",
    "scripts/grafana/generate-stage3-partner-dashboards.py",
}


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def dashboard_query_text(payload: dict) -> str:
    exprs: list[str] = []
    for panel in payload.get("panels", []):
        for target in panel.get("targets", []):
            if isinstance(target, dict):
                exprs.append(str(target.get("expr", "")))
    return "\n".join(exprs)


def names(kind: str, text: str) -> set[str]:
    return set(re.findall(rf"^\s*-\s*{kind}:\s*([^\s]+)\s*$", text, re.MULTILINE))


def main() -> int:
    for rel_path in REQUIRED_SCRIPTS:
        assert (ROOT / rel_path).exists(), f"Missing script {rel_path}"

    for filename, expected in REQUIRED_DASHBOARDS.items():
        payload = json.loads(read(DASHBOARD_DIR / filename))
        assert payload["uid"] == expected["uid"], f"{filename} uid mismatch"
        assert "stage3" in payload.get("tags", []), f"{filename} missing stage3 tag"
        query_text = dashboard_query_text(payload)
        for fragment in expected["fragments"]:
            assert fragment in query_text, f"{filename} missing query fragment {fragment!r}"

    rules_text = read(RULES_PATH)
    missing_rules = REQUIRED_RECORDING_RULES - names("record", rules_text)
    assert not missing_rules, f"Missing recording rules: {sorted(missing_rules)}"
    missing_alerts = REQUIRED_ALERTS - names("alert", rules_text)
    assert not missing_alerts, f"Missing alerts: {sorted(missing_alerts)}"
    for fragment in ("stage: s3", "priority: p0", "priority: p1", "runbook_path:", "dashboard_path:"):
        assert fragment in rules_text, f"Missing alert fragment {fragment!r}"

    targets = json.loads(read(TARGETS_PATH))
    target_values = [target for group in targets for target in group.get("targets", [])]
    assert target_values, "Stage 3 storefront targets are empty"
    assert all("h.cyber-vpn.net" in target for target in target_values)
    assert all("ozoxy.ru" not in target for target in target_values)
    assert "requires_dns_before_live_scrape" in json.dumps(targets)

    compose = read(COMPOSE_PATH)
    for fragment in ("profiles:", "manual", "127.0.0.1:9088:9088", "no-new-privileges:true", "read_only: true"):
        assert fragment in compose, f"Partner lab compose missing {fragment!r}"

    runbook = read(RUNBOOK_PATH)
    for fragment in ("Partner Lab", "Storefront Synthetic Checks", "Settlement And Payout Rules", "Redacted/Anonymized Data Import", "Partner Incidents"):
        assert fragment in runbook, f"Runbook missing {fragment!r}"
    read(PLAN_PATH)

    ci = read(ROOT / ".gitlab-ci.yml")
    for fragment in ("partner:stage3-artifacts:", "partner:stage3-sandbox-pack:", "scripts/validate-stage3-partner-artifacts.py"):
        assert fragment in ci, f"CI missing {fragment!r}"

    print("PASS: Stage 3 partner/reseller artifacts are wired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
