import json
import re
from pathlib import Path

REQUIRED_DASHBOARD_PANELS = {
    "API Up": {"stage1:target_up", 'job="cybervpn-local-backend"'},
    "Worker Up": {"stage1:target_up", 'job="cybervpn-worker"'},
    "Bot Up": {"stage1:target_up", 'job="cybervpn-telegram-bot"'},
    "PostgreSQL Up": {"stage1:target_up", 'job="postgres"'},
    "Redis Up": {"stage1:target_up", 'job="redis"'},
    "Remnawave Up": {"stage1:target_up", 'job="remnawave"'},
    "API HTTP P95": {"stage1:api_http_p95_seconds:5m"},
    "API Error and Auth Success": {"stage1:api_http_error_ratio:5m", "stage1:auth_success_ratio:5m"},
    "Payment Success Ratio 1h": {"stage1:payment_success_ratio:1h"},
    "Paid-But-No-Access Reconciliation": {
        "cybervpn_stage1_payment_reconciliation_items_current",
        "cybervpn_stage1_payment_reconciliation_max_age_minutes",
    },
    "Remnawave API Error Ratio": {"stage1:remnawave_external_error_ratio:5m"},
    "Worker Queue and Task Errors": {"cybervpn_queue_depth", "stage1:worker_task_error_ratio:5m"},
    "PostgreSQL Runtime": {"pg_stat_database_numbackends", "stage1:postgres_rollback_ratio:5m"},
    "Redis Runtime": {"stage1:redis_memory_used_bytes", "redis_rejected_connections_total"},
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
    "stage1:payment_success_ratio:1h",
    "stage1:payment_reconciliation_items:current",
    "stage1:worker_task_error_ratio:5m",
    "stage1:remnawave_external_error_ratio:5m",
    "stage1:postgres_rollback_ratio:5m",
    "stage1:redis_memory_used_bytes",
    "stage1:remnawave_healthy_nodes:current",
    "stage1:telegram_bot_error_ratio:5m",
}

REQUIRED_SCRAPE_JOBS = {
    "cybervpn-local-backend",
    "cybervpn-worker",
    "cybervpn-telegram-bot",
    "postgres",
    "redis",
    "remnawave",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _dashboard() -> dict:
    path = _repo_root() / "infra/grafana/dashboards/stage1-controlled-public-beta-dashboard.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _panel_index(dashboard: dict) -> dict[str, str]:
    panels: dict[str, str] = {}
    for panel in dashboard.get("panels", []):
        title = panel.get("title")
        if not title:
            continue
        panels[title] = "\n".join(
            target["expr"]
            for target in panel.get("targets", [])
            if isinstance(target, dict) and "expr" in target
        )
    return panels


def test_stage1_launch_dashboard_covers_required_s1_surfaces() -> None:
    dashboard = _dashboard()
    panels = _panel_index(dashboard)

    assert dashboard["uid"] == "stage1-controlled-public-beta"
    assert dashboard["title"] == "Stage 1 Controlled Public Beta"
    assert "stage1" in dashboard.get("tags", [])

    for panel_title, expected_fragments in REQUIRED_DASHBOARD_PANELS.items():
        assert panel_title in panels
        panel_query = panels[panel_title]
        for fragment in expected_fragments:
            assert fragment in panel_query


def test_stage1_recording_rules_are_loaded_by_prometheus_config() -> None:
    root = _repo_root()
    prometheus_config = (root / "infra/prometheus/prometheus.yml").read_text(encoding="utf-8")
    rules_text = (root / "infra/prometheus/rules/stage1_dashboard_recording_rules.yml").read_text(
        encoding="utf-8"
    )

    assert "stage1_dashboard_recording_rules.yml" in prometheus_config
    records = set(re.findall(r"^\s*-\s*record:\s*([^\s]+)\s*$", rules_text, re.MULTILINE))
    assert REQUIRED_RECORDING_RULES <= records


def test_stage1_prometheus_scrape_jobs_cover_dashboard_dependencies() -> None:
    prometheus_config = (_repo_root() / "infra/prometheus/prometheus.yml").read_text(encoding="utf-8")
    jobs = set(re.findall(r"job_name:\s*['\"]?([^'\"\n]+)['\"]?", prometheus_config))

    assert REQUIRED_SCRAPE_JOBS <= jobs
