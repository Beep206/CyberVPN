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
            "snapshot_id": "phase8-settlement-001",
            "source": "phase8-settlement-fixture",
            "replay_generated_at": "2026-04-19T18:00:00+00:00",
            "default_max_amount_delta": "0.00",
        },
        "phase4_snapshot": {
            "metadata": {
                "snapshot_id": "phase4-ref-001",
                "source": "phase8-settlement-fixture",
                "replay_generated_at": "2026-04-19T18:00:00+00:00",
            },
            "earning_events": [
                {
                    "id": "event-1",
                    "partner_account_id": "partner-1",
                    "event_status": "available",
                    "total_amount": "30.00",
                    "currency_code": "USD",
                    "created_at": "2026-04-19T10:00:00+00:00",
                },
                {
                    "id": "event-2",
                    "partner_account_id": "partner-1",
                    "event_status": "blocked",
                    "total_amount": "20.00",
                    "currency_code": "USD",
                    "created_at": "2026-04-19T10:01:00+00:00",
                },
            ],
            "earning_holds": [
                {
                    "id": "hold-1",
                    "earning_event_id": "event-2",
                    "partner_account_id": "partner-1",
                    "hold_status": "active",
                    "created_at": "2026-04-19T10:02:00+00:00",
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
                    "created_at": "2026-04-19T10:03:00+00:00",
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
                    "created_at": "2026-04-19T10:04:00+00:00",
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
                    "created_at": "2026-04-19T10:05:00+00:00",
                }
            ],
            "payout_instructions": [
                {
                    "id": "instruction-1",
                    "partner_account_id": "partner-1",
                    "partner_statement_id": "statement-1",
                    "partner_payout_account_id": "payout-account-1",
                    "instruction_status": "approved",
                    "payout_amount": "23.00",
                    "currency_code": "USD",
                    "created_at": "2026-04-19T10:06:00+00:00",
                }
            ],
            "payout_executions": [
                {
                    "id": "execution-dry-1",
                    "payout_instruction_id": "instruction-1",
                    "partner_account_id": "partner-1",
                    "partner_statement_id": "statement-1",
                    "partner_payout_account_id": "payout-account-1",
                    "execution_mode": "dry_run",
                    "execution_status": "reconciled",
                    "created_at": "2026-04-19T10:07:00+00:00",
                }
            ],
        },
        "analytical_snapshot": {
            "metadata": {
                "snapshot_id": "phase7-reporting-001",
                "source": "phase8-settlement-fixture",
                "replay_generated_at": "2026-04-19T18:00:00+00:00",
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
                    "created_at": "2026-04-19T10:10:00+00:00",
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
                    "created_at": "2026-04-19T10:11:00+00:00",
                }
            ],
            "commissionability_evaluations": [
                {
                    "id": "eval-1",
                    "order_id": "order-1",
                    "commissionability_status": "eligible",
                    "created_at": "2026-04-19T10:12:00+00:00",
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
                    "created_at": "2026-04-19T10:13:00+00:00",
                }
            ],
            "partner_statements": [
                {
                    "id": "statement-1",
                    "partner_account_id": "partner-1",
                    "currency_code": "USD",
                    "available_amount": "23.00",
                    "superseded_by_statement_id": None,
                    "created_at": "2026-04-19T10:14:00+00:00",
                }
            ],
            "outbox_events": [
                {
                    "id": "evt-1",
                    "event_family": "order",
                    "event_name": "order.created",
                    "created_at": "2026-04-19T10:15:00+00:00",
                }
            ],
            "outbox_publications": [
                {
                    "id": "pub-1",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "analytics_mart",
                    "publication_status": "published",
                    "created_at": "2026-04-19T10:16:00+00:00",
                },
                {
                    "id": "pub-2",
                    "outbox_event_id": "evt-1",
                    "consumer_key": "operational_replay",
                    "publication_status": "published",
                    "created_at": "2026-04-19T10:17:00+00:00",
                },
            ],
        },
        "statement_shadow_observations": [
            {
                "statement_id": "statement-1",
                "observed_statement_status": "closed",
                "observed_available_amount": "21.00",
                "observed_reserve_amount": "5.00",
                "observed_adjustment_net_amount": "-2.00",
            }
        ],
        "liability_shadow_observations": [
            {
                "partner_account_id": "partner-1",
                "observed_outstanding_statement_liability_amount": "18.00",
                "observed_completed_payout_amount": "0.00",
                "observed_total_active_reserve_amount": "5.00",
            }
        ],
        "payout_dry_run_observations": [
            {
                "payout_instruction_id": "instruction-1",
                "observed_instruction_status": "completed",
                "observed_execution_statuses": ["reconciled"],
                "observed_completed_payout_amount": "0.00",
                "observed_outstanding_statement_liability_amount": "23.00",
            }
        ],
        "partner_export_observations": [
            {
                "export_key": "partner-1-export-001",
                "workspace_id": "workspace-1",
                "partner_account_id": "partner-1",
                "export_status": "ready",
                "observed_paid_conversion_count": 1,
                "observed_available_earnings_amount": "29.50",
                "observed_statement_liability_amount": "23.00",
                "observed_currency_codes": ["USD"],
            }
        ],
        "amount_tolerances": [
            {
                "comparison_family": "statement",
                "metric_key": "available_amount",
                "max_delta_amount": "0.50",
            },
            {
                "comparison_family": "liability",
                "metric_key": "outstanding_statement_liability_amount",
                "max_delta_amount": "1.00",
            },
            {
                "comparison_family": "partner_export",
                "metric_key": "available_earnings_amount",
                "max_delta_amount": "0.25",
            },
        ],
        "approved_divergences": [],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase8_settlement_shadow_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase8_settlement_shadow_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase8_settlement_shadow_summary.py"
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
    assert report["metadata"]["report_version"] == "phase8-settlement-shadow-v1"
    assert report["metadata"]["generated_at"] == "2026-04-19T18:00:00+00:00"
    assert report["phase4_reference"]["status"] == "green"
    assert report["analytical_reference"]["status"] == "green"
    assert report["reconciliation"]["status"] == "red"
    assert report["reconciliation"]["mismatch_counts"]["statement_available_amount_delta_exceeded"] == 1
    assert report["reconciliation"]["mismatch_counts"]["liability_outstanding_statement_amount_delta_exceeded"] == 1
    assert report["reconciliation"]["mismatch_counts"]["payout_dry_run_instruction_status_mismatch"] == 1
    assert report["reconciliation"]["mismatch_counts"]["partner_export_available_earnings_amount_mismatch"] == 1
    assert report["pilot_finance_gate"]["blocking_statement_ids"] == ["statement-1"]
    assert report["pilot_finance_gate"]["blocking_partner_account_ids"] == ["partner-1"]
    assert report["pilot_finance_gate"]["blocking_payout_instruction_ids"] == ["instruction-1"]

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout
    assert "status: red" in stdout
    assert "phase4 reference: green" in stdout
    assert "analytical reference: green" in stdout
    assert "statement statement-1: available=23.0 status=red" in stdout
    assert "partner partner-1: outstanding=23.0 status=red" in stdout
    assert "statement_available_amount_delta_exceeded: 1" in stdout
    assert "partner_export_available_earnings_amount_mismatch: 1" in stdout


def test_phase8_settlement_shadow_doc_covers_vocabulary_and_tolerances() -> None:
    repo_root = _repo_root()
    content = (
        repo_root / "docs/testing/partner-platform-phase8-settlement-shadow-pack.md"
    ).read_text(encoding="utf-8")

    for required_term in (
        "replay_generated_at",
        "phase4_snapshot",
        "analytical_snapshot",
        "statement_shadow_observations",
        "liability_shadow_observations",
        "payout_dry_run_observations",
        "partner_export_observations",
        "amount_tolerances",
        "statement_available_amount_delta_exceeded",
        "liability_outstanding_statement_amount_delta_exceeded",
        "payout_dry_run_instruction_status_mismatch",
        "partner_export_available_earnings_amount_mismatch",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
