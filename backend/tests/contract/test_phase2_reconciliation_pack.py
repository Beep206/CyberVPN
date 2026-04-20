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
            "snapshot_id": "phase2-synthetic-001",
            "source": "legacy-payment-export",
            "replay_generated_at": "2026-04-18T10:00:00+00:00",
        },
        "payments": [
            {
                "id": "pay-1",
                "user_uuid": "user-1",
                "amount": "100.00",
                "final_amount": "90.00",
                "currency": "USD",
                "status": "completed",
                "provider": "stripe",
                "external_id": "ext-pay-1",
                "partner_code_id": "partner-code-1",
                "promo_code_id": "promo-code-1",
                "created_at": "2026-04-18T09:00:00+00:00",
            },
            {
                "id": "pay-2",
                "user_uuid": "user-2",
                "amount": "50.00",
                "final_amount": "50.00",
                "currency": "USD",
                "status": "refunded",
                "provider": "cryptobot",
                "external_id": "ext-pay-2",
                "created_at": "2026-04-18T09:10:00+00:00",
            },
        ],
        "refunds": [
            {
                "id": "refund-1",
                "payment_id": "pay-1",
                "amount": "10.00",
                "currency": "USD",
                "status": "succeeded",
                "external_reference": "refund-ext-1",
                "created_at": "2026-04-18T09:30:00+00:00",
            },
            {
                "id": "refund-orphan",
                "payment_id": "pay-missing",
                "amount": "5.00",
                "currency": "USD",
                "status": "succeeded",
                "external_reference": "refund-ext-missing",
                "created_at": "2026-04-18T09:35:00+00:00",
            },
        ],
        "payment_disputes": [
            {
                "id": "dispute-1",
                "payment_id": "pay-1",
                "amount": "15.00",
                "currency": "USD",
                "subtype": "chargeback",
                "outcome_class": "open",
                "lifecycle_status": "opened",
                "external_reference": "dispute-ext-1",
                "created_at": "2026-04-18T09:45:00+00:00",
            },
            {
                "id": "dispute-orphan",
                "payment_id": "pay-missing",
                "amount": "5.00",
                "currency": "USD",
                "subtype": "chargeback",
                "outcome_class": "open",
                "lifecycle_status": "opened",
                "external_reference": "dispute-ext-missing",
                "created_at": "2026-04-18T09:50:00+00:00",
            },
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase2_reconciliation_builder_script_emits_deterministic_pack_and_explains_mismatches(
    tmp_path: Path,
) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase2_order_reconciliation_pack.py"
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
    assert report["metadata"]["report_version"] == "phase2-order-reconciliation-v1"
    assert report["metadata"]["generated_at"] == "2026-04-18T10:00:00+00:00"
    assert report["reconciliation"]["status"] == "red"
    assert report["replayed_objects"]["orders"][0]["replay_order_id"] == "legacy-payment:pay-1"
    assert report["replayed_objects"]["payment_attempts"][0]["replay_payment_attempt_id"] == "legacy-attempt:pay-1:1"
    assert report["replayed_summary"]["orders"]["count"] == 2
    assert report["replayed_summary"]["refunds"]["count"] == 1
    assert report["replayed_summary"]["payment_disputes"]["count"] == 1
    assert report["reconciliation"]["mismatch_counts"]["orphan_refund_without_payment"] == 1
    assert report["reconciliation"]["mismatch_counts"]["orphan_payment_dispute_without_payment"] == 1
    assert report["reconciliation"]["mismatch_counts"]["payment_status_refunded_without_refund_rows"] == 1

    mismatch_codes = {item["code"] for item in report["reconciliation"]["mismatches"]}
    assert "orphan_refund_without_payment" in mismatch_codes
    assert "orphan_payment_dispute_without_payment" in mismatch_codes
    assert "payment_status_refunded_without_refund_rows" in mismatch_codes


def test_phase2_reconciliation_summary_script_prints_compact_status(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase2_order_reconciliation_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase2_order_reconciliation_summary.py"
    snapshot_path = tmp_path / "snapshot.json"
    report_path = tmp_path / "report.json"

    _write_snapshot(snapshot_path)

    subprocess.run(  # noqa: S603
        [sys.executable, str(builder), "--input", str(snapshot_path), "--output", str(report_path)],
        check=True,
        cwd=repo_root,
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(report_path)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )

    stdout = result.stdout
    assert "status: red" in stdout
    assert "legacy payments: 2" in stdout
    assert "replayed orders: 2" in stdout
    assert "orphan_refund_without_payment: 1" in stdout


def test_phase2_reconciliation_doc_covers_deterministic_replay_and_mismatch_vocabulary() -> None:
    repo_root = _repo_root()
    content = (
        repo_root / "docs/testing/partner-platform-phase2-reconciliation-pack.md"
    ).read_text(encoding="utf-8")

    for required_term in (
        "replay_generated_at",
        "orphan_refund_without_payment",
        "payment_status_refunded_without_refund_rows",
        "unsupported_payment_status",
        "legacy-payment:<payment_id>",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
