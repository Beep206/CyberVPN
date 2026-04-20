#!/usr/bin/env python3
"""Print a compact summary for a Phase 8 settlement shadow pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a compact Phase 8 settlement shadow summary.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to the settlement shadow pack JSON.")
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    reconciliation = dict(report.get("reconciliation") or {})

    print(f"status: {reconciliation.get('status', 'unknown')}")
    print(f"phase4 reference: {report.get('phase4_reference', {}).get('status', 'unknown')}")
    print(f"analytical reference: {report.get('analytical_reference', {}).get('status', 'unknown')}")

    for statement_view in report.get("statement_shadow_views", []):
        statement_totals = statement_view.get("canonical_statement_view", {}).get("statement_totals", {})
        print(
            f"statement {statement_view.get('statement_id')}: "
            f"available={statement_totals.get('available_amount')} "
            f"status={statement_view.get('status')}"
        )
    for liability_view in report.get("liability_shadow_views", []):
        liability_totals = liability_view.get("canonical_liability_view", {}).get("liability_totals", {})
        print(
            f"partner {liability_view.get('partner_account_id')}: "
            f"outstanding={liability_totals.get('outstanding_statement_liability_amount')} "
            f"status={liability_view.get('status')}"
        )
    for payout_view in report.get("payout_dry_run_views", []):
        print(
            f"dry-run {payout_view.get('payout_instruction_id')}: "
            f"status={payout_view.get('status')} "
            f"instruction_status={payout_view.get('canonical_payout_view', {}).get('instruction_status')}"
        )

    mismatch_counts = reconciliation.get("mismatch_counts") or {}
    for code in sorted(mismatch_counts):
        print(f"{code}: {mismatch_counts[code]}")


if __name__ == "__main__":
    main()
