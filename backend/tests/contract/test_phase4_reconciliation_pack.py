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
            "snapshot_id": "phase4-synthetic-001",
            "source": "phase4-evidence-fixture",
            "replay_generated_at": "2026-04-18T16:00:00+00:00",
        },
        "earning_events": [
            {
                "id": "event-1",
                "partner_account_id": "partner-1",
                "event_status": "available",
                "total_amount": "30.00",
                "currency_code": "USD",
                "created_at": "2026-04-18T10:00:00+00:00",
            },
            {
                "id": "event-2",
                "partner_account_id": "partner-1",
                "event_status": "blocked",
                "total_amount": "20.00",
                "currency_code": "USD",
                "created_at": "2026-04-18T10:05:00+00:00",
            },
            {
                "id": "event-3",
                "partner_account_id": "partner-1",
                "event_status": "reversed",
                "total_amount": "10.00",
                "currency_code": "USD",
                "created_at": "2026-04-18T10:06:00+00:00",
            },
        ],
        "earning_holds": [
            {
                "id": "hold-1",
                "earning_event_id": "event-2",
                "partner_account_id": "partner-1",
                "hold_status": "active",
                "created_at": "2026-04-18T10:07:00+00:00",
            }
        ],
        "reserves": [
            {
                "id": "reserve-1",
                "partner_account_id": "partner-1",
                "source_earning_event_id": "event-2",
                "reserve_scope": "earning_event",
                "reserve_reason_type": "dispute_buffer",
                "reserve_status": "active",
                "amount": "5.00",
                "currency_code": "USD",
                "created_at": "2026-04-18T10:08:00+00:00",
            }
        ],
        "statement_adjustments": [
            {
                "id": "adjustment-1",
                "partner_statement_id": "statement-1",
                "partner_account_id": "partner-1",
                "source_reference_type": "refund",
                "source_reference_id": "refund-1",
                "adjustment_type": "refund_clawback",
                "adjustment_direction": "debit",
                "amount": "2.00",
                "currency_code": "USD",
                "created_at": "2026-04-18T10:09:00+00:00",
            }
        ],
        "partner_statements": [
            {
                "id": "statement-1",
                "partner_account_id": "partner-1",
                "settlement_period_id": "period-1",
                "statement_status": "closed",
                "statement_version": 1,
                "superseded_by_statement_id": None,
                "reopened_from_statement_id": None,
                "currency_code": "USD",
                "accrual_amount": "50.00",
                "on_hold_amount": "20.00",
                "reserve_amount": "5.00",
                "adjustment_net_amount": "-2.00",
                "available_amount": "23.00",
                "source_event_count": 2,
                "held_event_count": 1,
                "active_reserve_count": 1,
                "adjustment_count": 1,
                "statement_snapshot": {
                    "window_start": "2026-04-01T00:00:00+00:00",
                    "window_end": "2026-05-01T00:00:00+00:00",
                    "currency_code": "USD",
                    "earning_event_ids": ["event-1", "event-2"],
                    "held_event_ids": ["event-2"],
                    "reserve_ids": ["reserve-1"],
                    "adjustment_ids": ["adjustment-1"],
                    "totals": {
                        "accrual_amount": 50.0,
                        "on_hold_amount": 20.0,
                        "reserve_amount": 5.0,
                        "adjustment_net_amount": -2.0,
                        "available_amount": 23.0,
                    },
                },
                "created_at": "2026-04-18T10:10:00+00:00",
            }
        ],
        "payout_instructions": [
            {
                "id": "instruction-1",
                "partner_account_id": "partner-1",
                "partner_statement_id": "statement-1",
                "partner_payout_account_id": "payout-account-1",
                "instruction_status": "completed",
                "payout_amount": "25.00",
                "currency_code": "USD",
                "created_at": "2026-04-18T10:11:00+00:00",
            }
        ],
        "payout_executions": [
            {
                "id": "execution-1",
                "payout_instruction_id": "instruction-1",
                "partner_account_id": "partner-1",
                "partner_statement_id": "statement-1",
                "partner_payout_account_id": "payout-account-1",
                "execution_mode": "live",
                "execution_status": "reconciled",
                "created_at": "2026-04-18T10:12:00+00:00",
            },
            {
                "id": "execution-orphan",
                "payout_instruction_id": "instruction-missing",
                "partner_account_id": "partner-1",
                "partner_statement_id": "statement-1",
                "partner_payout_account_id": "payout-account-1",
                "execution_mode": "live",
                "execution_status": "reconciled",
                "created_at": "2026-04-18T10:13:00+00:00",
            },
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase4_reconciliation_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase4_settlement_reconciliation_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase4_settlement_reconciliation_summary.py"
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
    assert report["metadata"]["report_version"] == "phase4-settlement-reconciliation-v1"
    assert report["metadata"]["generated_at"] == "2026-04-18T16:00:00+00:00"
    assert report["reconciliation"]["status"] == "red"
    assert report["input_summary"]["partner_statements"] == 1
    assert report["liability_views"][0]["reserve_totals"]["total_active_reserve_amount"] == 5.0
    assert report["liability_views"][0]["liability_totals"]["outstanding_statement_liability_amount"] == -2.0
    assert report["statement_views"][0]["recomputed_totals"]["available_amount"] == 23.0
    assert report["reconciliation"]["mismatch_counts"]["payout_instruction_amount_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["payout_execution_without_instruction"] == 1
    assert report["reconciliation"]["mismatch_counts"]["paid_amount_exceeds_statement_liability"] == 1

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout
    assert "status: red" in stdout
    assert "partner partner-1: available_statement=23.00" in stdout
    assert "payout_instruction_amount_mismatch: 1" in stdout


def test_phase4_reconciliation_doc_covers_liability_views_and_mismatch_vocabulary() -> None:
    repo_root = _repo_root()
    content = (
        repo_root / "docs/testing/partner-platform-phase4-settlement-reconciliation-pack.md"
    ).read_text(encoding="utf-8")

    for required_term in (
        "replay_generated_at",
        "liability_views",
        "statement_views",
        "payout_views",
        "payout_instruction_amount_mismatch",
        "payout_execution_without_instruction",
        "paid_amount_exceeds_statement_liability",
        "outstanding_statement_liability_amount",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
