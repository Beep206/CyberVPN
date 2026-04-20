#!/usr/bin/env python3
"""Print a compact summary for a Phase 4 settlement reconciliation pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_report(input_path: Path) -> dict:
    return json.loads(input_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a compact Phase 4 settlement reconciliation summary.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to the reconciliation pack JSON file.")
    args = parser.parse_args()

    report = _read_report(args.input)
    reconciliation = dict(report.get("reconciliation") or {})
    liability_views = list(report.get("liability_views") or [])

    print(f"status: {reconciliation.get('status', 'unknown')}")
    print(f"earning events: {report.get('input_summary', {}).get('earning_events', 0)}")
    print(f"partner statements: {report.get('input_summary', {}).get('partner_statements', 0)}")
    print(f"payout instructions: {report.get('input_summary', {}).get('payout_instructions', 0)}")
    print(f"payout executions: {report.get('input_summary', {}).get('payout_executions', 0)}")

    for view in liability_views:
        partner_account_id = view.get("partner_account_id", "unknown")
        liability = dict(view.get("liability_totals") or {})
        print(
            "partner "
            f"{partner_account_id}: available_statement={liability.get('available_statement_amount', 0.0):.2f}, "
            f"unstatemented={liability.get('available_unstatemented_amount', 0.0):.2f}, "
            f"paid={liability.get('completed_payout_amount', 0.0):.2f}, "
            f"outstanding={liability.get('outstanding_statement_liability_amount', 0.0):.2f}"
        )

    mismatch_counts = dict(reconciliation.get("mismatch_counts") or {})
    for code in sorted(mismatch_counts):
        print(f"{code}: {mismatch_counts[code]}")


if __name__ == "__main__":
    main()
