import re
from pathlib import Path

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

REQUIRED_RECEIVERS = {
    "stage1-p0",
    "stage1-p1",
    "stage1-critical",
    "stage1-warning",
    "stage1-default",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _alert_names(rules_text: str) -> set[str]:
    return set(re.findall(r"^\s*-\s*alert:\s*([A-Za-z0-9_]+)\s*$", rules_text, re.MULTILINE))


def test_stage1_alert_rules_are_loaded_and_cover_launch_blockers() -> None:
    root = _repo_root()
    prometheus_config = (root / "infra/prometheus/prometheus.yml").read_text(encoding="utf-8")
    rules_text = (root / "infra/prometheus/rules/stage1_alerts.yml").read_text(encoding="utf-8")

    assert "stage1_alerts.yml" in prometheus_config
    assert REQUIRED_STAGE1_ALERTS <= _alert_names(rules_text)

    for fragment in (
        "stage: s1",
        "priority: p0",
        "priority: p1",
        "cybervpn_stage1_payment_reconciliation_launch_blocked",
        "cybervpn_stage1_payment_reconciliation_items_current",
        "stage1:remnawave_external_error_ratio:5m",
        "stage1_backup_last_success_unixtime",
        "stage1_restore_drill_last_success_unixtime",
    ):
        assert fragment in rules_text


def test_stage1_alertmanager_routes_to_telegram_and_backup_email() -> None:
    root = _repo_root()
    template = (root / "infra/alertmanager/alertmanager.yml.template").read_text(encoding="utf-8")
    entrypoint = (root / "infra/alertmanager/docker-entrypoint.sh").read_text(encoding="utf-8")
    message_template = (root / "infra/alertmanager/templates/telegram.tmpl").read_text(
        encoding="utf-8"
    )

    for receiver in REQUIRED_RECEIVERS:
        assert f"name: '{receiver}'" in template

    for fragment in (
        "telegram_configs:",
        "email_configs:",
        "chat_id:",
        "bot_token:",
        "smtp_auth_password_file:",
        "${ALERTMANAGER_BACKUP_EMAIL}",
        "priority=\"p0\"",
        "priority=\"p1\"",
    ):
        assert fragment in template

    assert "telegram.stage1.message" in message_template
    assert "email.stage1.text" in message_template
    assert "ALERTMANAGER_REQUIRE_LIVE_RECEIVERS" in entrypoint
    assert "stage1-local-placeholder" in entrypoint


def test_stage1_alertmanager_env_contract_is_documented_for_compose() -> None:
    root = _repo_root()
    compose = (root / "infra/docker-compose.yml").read_text(encoding="utf-8")
    env_example = (root / "infra/.env.example").read_text(encoding="utf-8")

    required_env = {
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

    for env_name in required_env:
        assert env_name in compose
        assert env_name in env_example
