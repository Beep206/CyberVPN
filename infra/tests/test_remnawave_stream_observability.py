from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "infra/grafana/dashboards/remnawave-streams-dashboard.json"
RULES_PATH = REPO_ROOT / "infra/prometheus/rules/stage1_alerts.yml"
RULE_TEST_PATH = REPO_ROOT / "infra/prometheus/tests/remnawave_stream_alerts.test.yml"


def test_dashboard_covers_every_required_stream_signal_without_raw_payloads() -> None:
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    assert dashboard["uid"] == "remnawave-streams"
    serialized = json.dumps(dashboard, sort_keys=True)
    for metric in (
        "cybervpn_remnawave_stream_pending_current",
        "cybervpn_remnawave_stream_last_consumed_unixtime",
        "cybervpn_remnawave_stream_message_lag_seconds_bucket",
        "cybervpn_remnawave_stream_reclaimed_total",
        "cybervpn_remnawave_stream_parse_failures_total",
        "cybervpn_remnawave_stream_dead_letters_total",
        "cybervpn_remnawave_stream_retention_backlog",
    ):
        assert metric in serialized
    for forbidden in ("raw_payload", "request_headers", "client_ip", "user_agent"):
        assert forbidden not in serialized.lower()


def test_alerts_cover_failure_and_recovery_capable_stream_conditions() -> None:
    rules = RULES_PATH.read_text(encoding="utf-8")
    expected = {
        "Stage1RemnawaveStreamPendingStalled": "pending_current",
        "Stage1RemnawaveStreamConsumerStale": "last_consumed_unixtime",
        "Stage1RemnawaveStreamLagHigh": "message_lag_seconds_bucket",
        "Stage1RemnawaveStreamParseFailure": "parse_failures_total",
        "Stage1RemnawaveStreamReclaimSpike": "reclaimed_total",
        "Stage1RemnawaveStreamDeadLetterCreated": "dead_letters_total",
        "Stage1RemnawaveStreamRetentionBacklog": "retention_backlog",
    }
    for name, metric_fragment in expected.items():
        match = re.search(
            rf"- alert: {name}\n(?P<body>.*?)(?=\n\s+- alert:|\Z)",
            rules,
            flags=re.DOTALL,
        )
        assert match is not None
        body = match.group("body")
        assert metric_fragment in body
        assert "dashboard_path: \"/d/remnawave-streams/remnawave-redis-streams\"" in body
        assert "REMNAWAVE_3_4_3_UPGRADE.md" in body

    # Every alert expression is state-derived (gauge or bounded range query),
    # so returning the source metric below its threshold clears the alert;
    # no sticky recording-rule latch is permitted.
    assert "keep_firing_for:" not in "\n".join(
        re.search(
            rf"- alert: {name}\n(?P<body>.*?)(?=\n\s+- alert:|\Z)",
            rules,
            flags=re.DOTALL,
        ).group("body")
        for name in expected
    )


def test_promtool_scenarios_cover_firing_and_recovery() -> None:
    scenarios = RULE_TEST_PATH.read_text(encoding="utf-8")
    assert "pending entries fire and recover when the PEL drains" in scenarios
    assert "a stale consumer clears after a fresh terminal commit" in scenarios
    assert scenarios.count("exp_alerts: []") == 2
