#!/usr/bin/env python3
"""Validate S1 alerting assets without running Prometheus or Alertmanager."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PROMETHEUS_CONFIG_PATH = REPO_ROOT / "infra/prometheus/prometheus.yml"
STAGE1_ALERT_RULES_PATH = REPO_ROOT / "infra/prometheus/rules/stage1_alerts.yml"
ALERTMANAGER_TEMPLATE_PATH = REPO_ROOT / "infra/alertmanager/alertmanager.yml.template"
ALERTMANAGER_ENTRYPOINT_PATH = REPO_ROOT / "infra/alertmanager/docker-entrypoint.sh"
ALERTMANAGER_TELEGRAM_TEMPLATE_PATH = REPO_ROOT / "infra/alertmanager/templates/telegram.tmpl"
DOCKER_COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
INFRA_ENV_EXAMPLE_PATH = REPO_ROOT / "infra/.env.example"

REQUIRED_STAGE1_ALERTS = {
    "Stage1ApiUnavailable",
    "Stage1WorkerUnavailable",
    "Stage1TelegramBotUnavailable",
    "Stage1PostgresUnavailable",
    "Stage1RedisUnavailable",
    "Stage1RemnawaveUnavailable",
    "Stage1NoHealthyRemnawaveNodes",
    "Stage1PaidButNoAccessReviewNeeded",
    "Stage1PaidButNoAccessP1Escalation",
    "Stage1PaidButNoAccessP0Blocker",
    "Stage1PaymentSuccessRatioLow",
    "Stage1ProvisioningDependencyErrors",
    "Stage1ApiErrorRatioHigh",
    "Stage1ApiLatencyHigh",
    "Stage1WorkerQueueBacklog",
    "Stage1WorkerTaskErrorRatioHigh",
    "Stage1RedisRejectedConnections",
    "Stage1PostgresRollbackRatioHigh",
    "Stage1TelegramBotErrorRatioHigh",
    "Stage1PostgresBackupStale",
    "Stage1RestoreDrillEvidenceExpired",
}

REQUIRED_ALERTMANAGER_RECEIVERS = {
    "stage1-p0",
    "stage1-p1",
    "stage1-critical",
    "stage1-warning",
    "stage1-default",
}

REQUIRED_ALERTMANAGER_ENV = {
    "ALERTMANAGER_REQUIRE_LIVE_RECEIVERS",
    "ALERTMANAGER_TELEGRAM_BOT_TOKEN",
    "ALERTMANAGER_TELEGRAM_CHAT_ID",
    "ALERTMANAGER_BACKUP_EMAIL",
    "ALERTMANAGER_SMTP_FROM",
    "ALERTMANAGER_SMTP_SMARTHOST",
    "ALERTMANAGER_SMTP_HELLO",
    "ALERTMANAGER_SMTP_AUTH_USERNAME",
    "ALERTMANAGER_SMTP_PASSWORD",
    "ALERTMANAGER_SMTP_REQUIRE_TLS",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _alert_names(text: str) -> set[str]:
    return set(re.findall(r"^\s*-\s*alert:\s*([A-Za-z0-9_]+)\s*$", text, re.MULTILINE))


def main() -> int:
    prometheus_config = _read(PROMETHEUS_CONFIG_PATH)
    alert_rules = _read(STAGE1_ALERT_RULES_PATH)
    alertmanager_template = _read(ALERTMANAGER_TEMPLATE_PATH)
    alertmanager_entrypoint = _read(ALERTMANAGER_ENTRYPOINT_PATH)
    telegram_template = _read(ALERTMANAGER_TELEGRAM_TEMPLATE_PATH)
    compose = _read(DOCKER_COMPOSE_PATH)
    env_example = _read(INFRA_ENV_EXAMPLE_PATH)

    assert "stage1_alerts.yml" in prometheus_config

    missing_alerts = REQUIRED_STAGE1_ALERTS - _alert_names(alert_rules)
    assert not missing_alerts, f"Missing S1 alerts: {sorted(missing_alerts)}"

    for required_fragment in (
        "stage: s1",
        "priority: p0",
        "priority: p1",
        "dashboard_path:",
        "runbook_path:",
        "cybervpn_stage1_payment_reconciliation_launch_blocked",
        "cybervpn_stage1_payment_reconciliation_items_current",
        "stage1:remnawave_external_error_ratio:5m",
        "stage1_backup_last_success_unixtime",
        "stage1_restore_drill_last_success_unixtime",
    ):
        assert required_fragment in alert_rules, f"Missing alert rule fragment: {required_fragment}"

    for receiver in REQUIRED_ALERTMANAGER_RECEIVERS:
        assert f"name: '{receiver}'" in alertmanager_template

    for required_fragment in (
        "telegram_configs:",
        "email_configs:",
        "chat_id:",
        "bot_token:",
        "smtp_auth_password_file:",
        "${ALERTMANAGER_BACKUP_EMAIL}",
        "priority=\"p0\"",
        "priority=\"p1\"",
    ):
        assert required_fragment in alertmanager_template, (
            f"Missing Alertmanager fragment: {required_fragment}"
        )

    for required_template in ("telegram.stage1.message", "email.stage1.text"):
        assert required_template in telegram_template

    for required_env in REQUIRED_ALERTMANAGER_ENV:
        assert required_env in compose, f"Missing compose env: {required_env}"
        assert required_env in env_example, f"Missing env example: {required_env}"

    for required_entrypoint_fragment in (
        "ALERTMANAGER_REQUIRE_LIVE_RECEIVERS",
        "ALERTMANAGER_TELEGRAM_BOT_TOKEN",
        "ALERTMANAGER_TELEGRAM_CHAT_ID",
        "ALERTMANAGER_SMTP_PASSWORD_FILE",
        "stage1-local-placeholder",
    ):
        assert required_entrypoint_fragment in alertmanager_entrypoint

    print("PASS: S1 alert rules and Alertmanager Telegram/email routing are wired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
