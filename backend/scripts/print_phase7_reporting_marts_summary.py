#!/usr/bin/env python3
"""Print a compact summary for a Phase 7 reporting marts pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_report(input_path: Path) -> dict:
    return json.loads(input_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a compact Phase 7 reporting marts summary.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to the reporting marts pack JSON file.")
    args = parser.parse_args()

    report = _read_report(args.input)
    reconciliation = dict(report.get("reconciliation") or {})
    partner_rows = list(report.get("partner_reporting_mart") or [])
    health_views = dict(report.get("reporting_health_views") or {})

    print(f"status: {reconciliation.get('status', 'unknown')}")
    print(f"orders: {report.get('input_summary', {}).get('orders', 0)}")
    print(f"partners: {len(partner_rows)}")
    print(f"outbox events: {report.get('input_summary', {}).get('outbox_events', 0)}")

    for row in partner_rows:
        print(
            "partner "
            f"{row.get('partner_account_id')}: paid={row.get('paid_conversion_count', 0)}, "
            f"qualifying_first={row.get('qualifying_first_payment_count', 0)}, "
            f"refund_rate={row.get('refund_rate', 0.0):.2f}, "
            f"chargeback_rate={row.get('chargeback_rate', 0.0):.2f}, "
            f"liability={row.get('statement_liability_amount', 0.0):.2f}"
        )

    for consumer in health_views.get("consumer_health_views", []):
        print(
            "consumer "
            f"{consumer.get('consumer_key')}: published={consumer.get('published_count', 0)}, "
            f"failed={consumer.get('failed_count', 0)}, "
            f"backlog={consumer.get('backlog_count', 0)}"
        )

    mismatch_counts = dict(reconciliation.get("mismatch_counts") or {})
    for code in sorted(mismatch_counts):
        print(f"{code}: {mismatch_counts[code]}")


if __name__ == "__main__":
    main()
