from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _write_snapshot(path: Path) -> None:
    snapshot = {
        "metadata": {
            "snapshot_id": "phase7-synthetic-001",
            "source": "phase7-evidence-fixture",
            "replay_generated_at": "2026-04-18T20:00:00+00:00",
        },
        "orders": [
            {
                "id": "order-1",
                "user_id": "user-1",
                "sale_channel": "web",
                "currency_code": "USD",
                "order_status": "committed",
                "settlement_status": "paid",
                "commission_base_amount": "50.00",
                "displayed_price": "50.00",
                "created_at": "2026-04-18T10:00:00+00:00",
            },
            {
                "id": "order-2",
                "user_id": "user-1",
                "sale_channel": "web",
                "currency_code": "USD",
                "order_status": "committed",
                "settlement_status": "paid",
                "commission_base_amount": "40.00",
                "displayed_price": "40.00",
                "created_at": "2026-04-18T11:00:00+00:00",
            },
            {
                "id": "order-3",
                "user_id": "user-2",
                "sale_channel": "telegram",
                "currency_code": "USD",
                "order_status": "committed",
                "settlement_status": "paid",
                "commission_base_amount": "25.00",
                "displayed_price": "25.00",
                "created_at": "2026-04-18T12:00:00+00:00",
            },
            {
                "id": "order-4",
                "user_id": "user-3",
                "sale_channel": "web",
                "currency_code": "USD",
                "order_status": "committed",
                "settlement_status": "pending_payment",
                "commission_base_amount": "15.00",
                "displayed_price": "15.00",
                "created_at": "2026-04-18T12:30:00+00:00",
            },
        ],
        "order_attribution_results": [
            {
                "id": "attr-1",
                "order_id": "order-1",
                "partner_account_id": "partner-1",
                "partner_code_id": "code-1",
                "owner_type": "affiliate",
                "owner_source": "explicit_code",
                "created_at": "2026-04-18T10:01:00+00:00",
            },
            {
                "id": "attr-2",
                "order_id": "order-2",
                "partner_account_id": "partner-1",
                "partner_code_id": "code-1",
                "owner_type": "affiliate",
                "owner_source": "explicit_code",
                "created_at": "2026-04-18T11:01:00+00:00",
            },
            {
                "id": "attr-3",
                "order_id": "order-3",
                "partner_account_id": "partner-2",
                "partner_code_id": "code-2",
                "owner_type": "affiliate",
                "owner_source": "explicit_code",
                "created_at": "2026-04-18T12:01:00+00:00",
            },
        ],
        "commissionability_evaluations": [
            {
                "id": "eval-1",
                "order_id": "order-1",
                "commissionability_status": "eligible",
                "created_at": "2026-04-18T10:02:00+00:00",
            },
            {
                "id": "eval-2",
                "order_id": "order-2",
                "commissionability_status": "eligible",
                "created_at": "2026-04-18T11:02:00+00:00",
            },
            {
                "id": "eval-3",
                "order_id": "order-3",
                "commissionability_status": "eligible",
                "created_at": "2026-04-18T12:02:00+00:00",
            },
        ],
        "renewal_orders": [
            {
                "id": "renewal-2",
                "order_id": "order-2",
                "effective_partner_account_id": "partner-1",
                "effective_partner_code_id": "code-1",
                "effective_owner_type": "affiliate",
                "effective_owner_source": "initial_order_inheritance",
                "created_at": "2026-04-18T11:03:00+00:00",
            }
        ],
        "refunds": [
            {
                "id": "refund-1",
                "order_id": "order-2",
                "refund_status": "succeeded",
                "created_at": "2026-04-18T11:30:00+00:00",
            }
        ],
        "payment_disputes": [
            {
                "id": "dispute-1",
                "order_id": "order-3",
                "outcome_class": "lost",
                "created_at": "2026-04-18T12:30:00+00:00",
            }
        ],
        "earning_events": [
            {
                "id": "earning-1",
                "partner_account_id": "partner-1",
                "currency_code": "USD",
                "available_amount": "30.00",
                "created_at": "2026-04-18T13:00:00+00:00",
            },
            {
                "id": "earning-2",
                "partner_account_id": "partner-2",
                "currency_code": "USD",
                "available_amount": "5.00",
                "created_at": "2026-04-18T13:10:00+00:00",
            },
        ],
        "partner_statements": [
            {
                "id": "statement-1",
                "partner_account_id": "partner-1",
                "currency_code": "USD",
                "available_amount": "28.00",
                "superseded_by_statement_id": None,
                "created_at": "2026-04-18T14:00:00+00:00",
            },
            {
                "id": "statement-2",
                "partner_account_id": "partner-2",
                "currency_code": "USD",
                "available_amount": "4.00",
                "superseded_by_statement_id": None,
                "created_at": "2026-04-18T14:10:00+00:00",
            },
        ],
        "outbox_events": [
            {
                "id": "evt-1",
                "event_family": "order",
                "event_name": "order.created",
                "created_at": "2026-04-18T15:00:00+00:00",
            },
            {
                "id": "evt-2",
                "event_family": "settlement",
                "event_name": "settlement.statement.generated",
                "created_at": "2026-04-18T15:05:00+00:00",
            },
        ],
        "outbox_publications": [
            {
                "id": "pub-1",
                "outbox_event_id": "evt-1",
                "consumer_key": "analytics_mart",
                "publication_status": "published",
                "created_at": "2026-04-18T15:00:30+00:00",
            },
            {
                "id": "pub-2",
                "outbox_event_id": "evt-1",
                "consumer_key": "operational_replay",
                "publication_status": "published",
                "created_at": "2026-04-18T15:00:40+00:00",
            },
            {
                "id": "pub-3",
                "outbox_event_id": "evt-2",
                "consumer_key": "analytics_mart",
                "publication_status": "failed",
                "created_at": "2026-04-18T15:05:30+00:00",
            },
            {
                "id": "pub-4",
                "outbox_event_id": "evt-2",
                "consumer_key": "operational_replay",
                "publication_status": "published",
                "created_at": "2026-04-18T15:05:40+00:00",
            },
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase7_reporting_marts_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase7_reporting_marts_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase7_reporting_marts_summary.py"
    snapshot_path = tmp_path / "snapshot.json"
    output_a = tmp_path / "report-a.json"
    output_b = tmp_path / "report-b.json"

    _write_snapshot(snapshot_path)

    for output_path in (output_a, output_b):
        subprocess.run(  # noqa: S603
            [sys.executable, str(builder), "--input", str(snapshot_path), "--output", str(output_path)],
            check=True,
            cwd=repo_root,
        )

    first = output_a.read_text(encoding="utf-8")
    second = output_b.read_text(encoding="utf-8")
    assert first == second

    report = json.loads(first)
    assert report["metadata"]["report_version"] == "phase7-reporting-marts-v1"
    assert report["metadata"]["generated_at"] == "2026-04-18T20:00:00+00:00"
    assert report["reconciliation"]["status"] == "yellow"
    assert report["input_summary"]["orders"] == 4
    assert report["order_reporting_mart"][0]["is_qualifying_first_payment"] is True
    assert report["order_reporting_mart"][1]["is_renewal"] is True

    partner_one = next(item for item in report["partner_reporting_mart"] if item["partner_account_id"] == "partner-1")
    assert partner_one["paid_conversion_count"] == 1
    assert partner_one["qualifying_first_payment_count"] == 1
    assert partner_one["refund_rate"] == 100.0
    assert partner_one["statement_liability_amount"] == 28.0

    consumer_health = {
        item["consumer_key"]: item for item in report["reporting_health_views"]["consumer_health_views"]
    }
    assert consumer_health["analytics_mart"]["failed_count"] == 1
    assert report["reconciliation"]["mismatch_counts"]["reporting_publication_failed"] == 1
    assert report["reconciliation"]["mismatch_counts"]["committed_order_missing_attribution_result"] == 1

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout
    assert "status: yellow" in stdout
    assert "partner partner-1: paid=1, qualifying_first=1" in stdout
    assert "consumer analytics_mart: published=1, failed=1, backlog=0" in stdout
    assert "reporting_publication_failed: 1" in stdout


def test_phase7_reporting_marts_doc_covers_marts_and_mismatch_vocabulary() -> None:
    repo_root = _repo_root()
    content = (
        repo_root / "docs/testing/partner-platform-phase7-analytical-marts-and-reconciliation-pack.md"
    ).read_text(encoding="utf-8")

    for required_term in (
        "order_reporting_mart",
        "partner_reporting_mart",
        "reporting_health_views",
        "outbox_event_missing_required_publication",
        "reporting_publication_failed",
        "committed_order_missing_attribution_result",
        "qualifying_first_payment_count",
        "statement_liability_amount",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
