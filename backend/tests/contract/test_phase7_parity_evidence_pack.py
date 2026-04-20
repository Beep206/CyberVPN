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
            "snapshot_id": "phase7-parity-001",
            "source": "phase7-parity-fixture",
            "replay_generated_at": "2026-04-19T09:00:00+00:00",
        },
        "analytical_snapshot": {
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
                    "created_at": "2026-04-19T08:00:00+00:00",
                }
            ],
            "order_attribution_results": [
                {
                    "id": "attr-1",
                    "order_id": "order-1",
                    "partner_account_id": "partner-1",
                    "partner_code_id": "code-1",
                    "owner_type": "affiliate",
                    "owner_source": "explicit_code",
                    "created_at": "2026-04-19T08:01:00+00:00",
                }
            ],
            "commissionability_evaluations": [
                {
                    "id": "eval-1",
                    "order_id": "order-1",
                    "commissionability_status": "eligible",
                    "created_at": "2026-04-19T08:02:00+00:00",
                }
            ],
            "renewal_orders": [],
            "refunds": [],
            "payment_disputes": [],
            "earning_events": [
                {
                    "id": "earning-1",
                    "partner_account_id": "partner-1",
                    "currency_code": "USD",
                    "available_amount": "30.00",
                    "created_at": "2026-04-19T08:10:00+00:00",
                }
            ],
            "partner_statements": [
                {
                    "id": "statement-1",
                    "partner_account_id": "partner-1",
                    "currency_code": "USD",
                    "available_amount": "28.00",
                    "superseded_by_statement_id": None,
                    "created_at": "2026-04-19T08:20:00+00:00",
                }
            ],
            "outbox_events": [
                {
                    "id": "evt-1",
                    "event_family": "order",
                    "event_name": "order.created",
                    "created_at": "2026-04-19T08:30:00+00:00",
                }
            ],
            "outbox_publications": [
                {
                    "id": "pub-1",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "analytics_mart",
                    "publication_status": "published",
                    "created_at": "2026-04-19T08:31:00+00:00",
                },
                {
                    "id": "pub-2",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "operational_replay",
                    "publication_status": "published",
                    "created_at": "2026-04-19T08:32:00+00:00",
                },
                {
                    "id": "pub-3",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "postback",
                    "publication_status": "failed",
                    "created_at": "2026-04-19T08:33:00+00:00",
                },
            ],
        },
        "channel_parity_expectations": [
            {
                "parity_key": "customer-1-main",
                "reference_channel": "official_web",
                "required_channels": ["official_web", "telegram_bot", "desktop_app"],
                "expected_paid_order_count": 1,
                "expected_active_entitlement_count": 1,
                "expected_service_state_status": "active",
                "expected_visible_order_ids": ["order-1"],
            }
        ],
        "channel_parity_observations": [
            {
                "parity_key": "customer-1-main",
                "channel_key": "official_web",
                "observed_paid_order_count": 1,
                "observed_active_entitlement_count": 1,
                "observed_service_state_status": "active",
                "observed_visible_order_ids": ["order-1"],
            },
            {
                "parity_key": "customer-1-main",
                "channel_key": "desktop_app",
                "observed_paid_order_count": 0,
                "observed_active_entitlement_count": 1,
                "observed_service_state_status": "active",
                "observed_visible_order_ids": [],
            },
        ],
        "partner_export_observations": [
            {
                "export_key": "partner-1-export-001",
                "workspace_id": "workspace-1",
                "partner_account_id": "partner-1",
                "export_status": "ready",
                "observed_paid_conversion_count": 1,
                "observed_available_earnings_amount": "25.00",
                "observed_statement_liability_amount": "28.00",
                "observed_currency_codes": ["USD"],
            }
        ],
        "postback_delivery_observations": [
            {
                "delivery_key": "postback-1",
                "workspace_id": "workspace-1",
                "partner_account_id": "partner-1",
                "outbox_event_id": "evt-1",
                "consumer_key": "postback",
                "observed_delivery_status": "delivered",
            }
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase7_parity_evidence_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase7_parity_evidence_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase7_parity_evidence_summary.py"
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
    assert report["metadata"]["report_version"] == "phase7-parity-evidence-v1"
    assert report["metadata"]["generated_at"] == "2026-04-19T09:00:00+00:00"
    assert report["analytical_reference"]["status"] == "yellow"
    assert report["reconciliation"]["status"] == "red"
    assert report["channel_coverage"]["additional_channel_count"] == 1
    assert report["channel_parity_views"][0]["parity_key"] == "customer-1-main"
    assert set(report["channel_parity_views"][0]["mismatch_codes"]) == {
        "channel_active_entitlement_count_mismatch",
        "channel_paid_order_count_mismatch",
        "channel_parity_missing_required_channel",
        "channel_visible_order_ids_mismatch",
    } - {"channel_active_entitlement_count_mismatch"}
    assert report["partner_export_views"][0]["mismatch_codes"] == [
        "partner_export_available_earnings_amount_mismatch"
    ]
    assert report["postback_delivery_views"][0]["mismatch_codes"] == ["postback_delivery_status_mismatch"]
    assert report["reconciliation"]["mismatch_counts"]["analytical_reference_not_green"] == 1
    assert report["reconciliation"]["mismatch_counts"]["channel_parity_missing_required_channel"] == 1
    assert report["reconciliation"]["mismatch_counts"]["channel_paid_order_count_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["channel_visible_order_ids_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["channel_parity_additional_channel_coverage_insufficient"] == 1
    assert report["reconciliation"]["mismatch_counts"]["partner_export_available_earnings_amount_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["postback_delivery_status_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["postback_publication_failed"] == 1

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout
    assert "status: red" in stdout
    assert "analytical reference: yellow" in stdout
    assert "additional channels: 1 (desktop_app)" in stdout
    assert "parity customer-1-main:" in stdout
    assert "partner_export_available_earnings_amount_mismatch: 1" in stdout
    assert "postback_delivery_status_mismatch: 1" in stdout


def test_phase7_parity_evidence_doc_covers_vocabulary() -> None:
    repo_root = _repo_root()
    content = (repo_root / "docs/testing/partner-platform-phase7-parity-and-evidence-pack.md").read_text(
        encoding="utf-8"
    )

    for required_term in (
        "replay_generated_at",
        "channel_parity_expectations",
        "channel_parity_observations",
        "partner_export_observations",
        "postback_delivery_observations",
        "channel_parity_missing_required_channel",
        "channel_paid_order_count_mismatch",
        "partner_export_available_earnings_amount_mismatch",
        "postback_delivery_status_mismatch",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
