#!/usr/bin/env python3
"""Generate CyberVPN Stage 3 partner/reseller Grafana dashboard JSON files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT / "infra" / "grafana" / "dashboards"
PROM = {"type": "prometheus", "uid": "${datasource}"}
LOKI = {"type": "loki", "uid": "${loki_datasource}"}
RUNBOOK_URL = "https://github.com/Beep206/CyberVPN/blob/main/docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md"


def target(expr: str, datasource: dict[str, str] | None = None, ref_id: str = "A") -> dict:
    return {
        "datasource": datasource or PROM,
        "editorMode": "code",
        "expr": expr,
        "legendFormat": "{{surface}} {{result}} {{reason}} {{payout_state}} {{instance}}",
        "range": True,
        "refId": ref_id,
    }


def panel(
    panel_id: int,
    title: str,
    kind: str,
    expr: str,
    x: int,
    y: int,
    w: int,
    h: int,
    unit: str = "none",
    datasource: dict[str, str] | None = None,
) -> dict:
    return {
        "datasource": datasource or PROM,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "orange", "value": 1},
                        {"color": "red", "value": 5},
                    ],
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
        "targets": [target(expr, datasource=datasource)],
        "title": title,
        "type": kind,
    }


def stat(panel_id: int, title: str, expr: str, x: int, y: int, unit: str = "none") -> dict:
    return panel(panel_id, title, "stat", expr, x, y, 6, 5, unit)


def timeseries(panel_id: int, title: str, expr: str, x: int, y: int, w: int = 12, unit: str = "none") -> dict:
    return panel(panel_id, title, "timeseries", expr, x, y, w, 8, unit)


def table(panel_id: int, title: str, expr: str, x: int, y: int, w: int = 24) -> dict:
    payload = panel(panel_id, title, "table", expr, x, y, w, 8)
    payload["options"] = {
        "cellHeight": "sm",
        "footer": {"countRows": False, "fields": "", "reducer": ["sum"], "show": False},
        "showHeader": True,
    }
    return payload


def logs(panel_id: int, title: str, expr: str, x: int, y: int, w: int = 24) -> dict:
    return {
        "datasource": LOKI,
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
        "targets": [{"datasource": LOKI, "expr": expr, "refId": "A"}],
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
        "links": [
            {
                "asDropdown": False,
                "icon": "external link",
                "includeVars": True,
                "keepTime": True,
                "targetBlank": True,
                "title": "Stage 3 Partner Runbook",
                "type": "link",
                "url": RUNBOOK_URL,
            }
        ],
        "panels": panels,
        "refresh": "30s",
        "schemaVersion": 41,
        "style": "dark",
        "tags": ["cybervpn", "stage3", "partner", *tags],
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
                    "label": "Surface",
                    "multi": True,
                    "name": "surface",
                    "options": [],
                    "query": "partner_portal,admin_portal,storefront,webhook_receiver,partner_lab",
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
    "stage3-partner-staging-readiness-dashboard.json": dashboard(
        "stage3-partner-staging-readiness",
        "Stage 3 Partner Staging Readiness",
        "Partner staging readiness across portal runtime, CI, storefront synthetic checks, and webhook test receiver.",
        ["staging", "readiness", "ci"],
        [
            stat(1, "Bootstrap Success Ratio", "stage3:partner_bootstrap_success_ratio:5m", 0, 0, "percentunit"),
            stat(2, "Frontend Error Events 15m", "stage3:partner_frontend_error_events:15m", 6, 0),
            stat(3, "Storefront Synthetic Success", "stage3:storefront_synthetic_success_ratio:5m", 12, 0, "percentunit"),
            stat(4, "Webhook Receiver Failures 15m", "stage3:partner_webhook_receiver_failures:15m", 18, 0),
            timeseries(5, "Partner Bootstrap And Auth", "stage3:partner_bootstrap_success_ratio:5m or stage3:partner_auth_denials:15m", 0, 5, 12),
            timeseries(6, "Partner Frontend UX", "stage3:partner_frontend_route_p95_seconds or stage3:partner_frontend_api_p95_seconds or stage3:partner_frontend_error_events:15m", 12, 5, 12, "s"),
            table(7, "Stage 3 Public Targets", "probe_success{job=\"stage3-storefront-endpoints\"} or vector(0)", 0, 13),
            logs(8, "Partner Staging Runtime Logs", "{container=~\".*(partner|backend|caddy).*\"} |~ \"partner|storefront|stage3|webhook\" |~ \"error|failed|denied|blocked\"", 0, 21),
        ],
    ),
    "stage3-partner-attribution-storefront-dashboard.json": dashboard(
        "stage3-partner-attribution-storefront",
        "Stage 3 Partner Attribution And Storefront",
        "Referral attribution, storefront synthetic checks, tracking touchpoints, conflicts, and no-owner resolution risk.",
        ["attribution", "storefront", "referral"],
        [
            stat(1, "Attribution No Owner Ratio", "stage3:partner_attribution_no_owner_ratio:5m", 0, 0, "percentunit"),
            stat(2, "Touchpoint Rejects 1h", "stage3:partner_touchpoint_rejects:1h", 6, 0),
            stat(3, "Referral Reward Reversals 24h", "stage3:partner_referral_reward_reversals:24h", 12, 0),
            stat(4, "Storefront Synthetic Failures 15m", "stage3:storefront_synthetic_failures:15m", 18, 0),
            timeseries(5, "Attribution Resolution Outcomes", "sum by (owner_type, owner_source, result, reason) (increase(cybervpn_partner_attribution_resolutions_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "Growth Code And Referral Flow", "sum by (surface, result) (increase(cybervpn_invites_redeemed_total[1h])) or sum by (surface, result) (increase(cybervpn_referral_rewards_created_total[1h])) or vector(0)", 12, 5, 12),
            table(7, "Rejected Touchpoints By Reason", "sum by (touchpoint_type, reason) (increase(cybervpn_partner_touchpoints_rejected_total[24h])) or vector(0)", 0, 13),
            logs(8, "Attribution And Storefront Exceptions", "{container=~\".*(partner|backend|worker).*\"} |~ \"attribution|touchpoint|storefront|referral\" |~ \"error|failed|rejected|conflict\"", 0, 21),
        ],
    ),
    "stage3-partner-settlement-payout-dashboard.json": dashboard(
        "stage3-partner-settlement-payout",
        "Stage 3 Partner Settlement And Payout",
        "Commission ledger, statement, payout simulation, settlement dry-run, and finance integrity signals.",
        ["settlement", "payout", "finance"],
        [
            stat(1, "Statement Closes 1h", "stage3:partner_statement_closes:1h", 0, 0),
            stat(2, "Payout Failures 15m", "stage3:partner_payout_failures:15m", 6, 0),
            stat(3, "Commission Ledger Mismatches 24h", "stage3:partner_commission_ledger_mismatches:24h", 12, 0),
            stat(4, "Settlement Dry-Run Failures 24h", "stage3:partner_settlement_dry_run_failures:24h", 18, 0),
            timeseries(5, "Payout Execution Outcomes", "sum by (payout_state, result) (increase(cybervpn_partner_payout_executions_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "Settlement Dry-Run And Payout Simulation", "sum by (result) (increase(cybervpn_partner_settlement_dry_run_total[1h])) or sum by (result) (increase(cybervpn_partner_payout_simulation_total[1h])) or vector(0)", 12, 5, 12),
            table(7, "Commission Ledger Drift By Severity", "sum by (severity, reason) (cybervpn_partner_commission_ledger_mismatch_current) or vector(0)", 0, 13),
            logs(8, "Settlement And Payout Exceptions", "{container=~\".*(backend|worker).*\"} |~ \"settlement|statement|payout|commission\" |~ \"error|failed|mismatch|dry-run\"", 0, 21),
        ],
    ),
    "stage3-partner-support-audit-risk-dashboard.json": dashboard(
        "stage3-partner-support-audit-risk",
        "Stage 3 Partner Support Audit Risk",
        "Partner support cases, audit log posture, risk review, anti-fraud experiment, and governance signals.",
        ["support", "audit", "risk"],
        [
            stat(1, "Partner Cases 24h", "stage3:partner_cases_created:24h", 0, 0),
            stat(2, "Risk Reviews Open", "stage3:partner_risk_reviews_open", 6, 0),
            stat(3, "Audit Log Failures 1h", "stage3:partner_audit_log_failures:1h", 12, 0),
            stat(4, "Anti-Fraud Flags 24h", "stage3:partner_antifraud_flags:24h", 18, 0),
            timeseries(5, "Case And Notification Flow", "sum by (case_type, result) (increase(cybervpn_partner_cases_created_total[1h])) or sum by (notification_type, result) (increase(cybervpn_partner_notifications_generated_total[1h])) or vector(0)", 0, 5, 12),
            timeseries(6, "Risk And Anti-Fraud Experiments", "sum by (experiment, result) (increase(cybervpn_partner_antifraud_experiment_total[1h])) or sum by (review_type, severity) (cybervpn_partner_risk_reviews_open) or vector(0)", 12, 5, 12),
            table(7, "Audit Failures By Action", "sum by (action, reason) (increase(cybervpn_partner_audit_log_failures_total[24h])) or vector(0)", 0, 13),
            logs(8, "Partner Support/Audit/Risk Logs", "{container=~\".*(backend|worker).*\"} |~ \"partner|risk|fraud|audit|case|governance\" |~ \"error|failed|blocked|denied\"", 0, 21),
        ],
    ),
}


def main() -> int:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    for filename, payload in DASHBOARDS.items():
        path = DASHBOARD_DIR / filename
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
