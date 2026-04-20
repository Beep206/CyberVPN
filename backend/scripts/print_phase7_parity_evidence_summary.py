#!/usr/bin/env python3
"""Print a compact summary for a Phase 7 parity evidence pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_report(input_path: Path) -> dict:
    return json.loads(input_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a compact Phase 7 parity evidence summary.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to the Phase 7 parity pack JSON file.")
    args = parser.parse_args()

    report = _read_report(args.input)
    reconciliation = dict(report.get("reconciliation") or {})
    analytical_reference = dict(report.get("analytical_reference") or {})
    channel_coverage = dict(report.get("channel_coverage") or {})

    print(f"status: {reconciliation.get('status', 'unknown')}")
    print(f"analytical reference: {analytical_reference.get('status', 'unknown')}")
    print(f"channel parity expectations: {report.get('input_summary', {}).get('channel_parity_expectations', 0)}")
    print(f"partner exports: {report.get('input_summary', {}).get('partner_export_observations', 0)}")
    print(f"postbacks: {report.get('input_summary', {}).get('postback_delivery_observations', 0)}")
    print(
        "additional channels: "
        f"{channel_coverage.get('additional_channel_count', 0)} "
        f"({', '.join(channel_coverage.get('additional_channels', [])) or 'none'})"
    )

    for view in report.get("channel_parity_views", []):
        print(
            "parity "
            f"{view.get('parity_key')}: status={view.get('status')}, "
            f"channels={','.join(view.get('observed_channels', [])) or 'none'}, "
            f"mismatches={','.join(view.get('mismatch_codes', [])) or 'none'}"
        )

    for view in report.get("partner_export_views", []):
        print(
            "export "
            f"{view.get('export_key')}: status={view.get('export_status')}, "
            f"mismatches={','.join(view.get('mismatch_codes', [])) or 'none'}"
        )

    for view in report.get("postback_delivery_views", []):
        print(
            "postback "
            f"{view.get('delivery_key')}: observed={view.get('observed_delivery_status')}, "
            f"publication={view.get('publication_status') or 'missing'}, "
            f"mismatches={','.join(view.get('mismatch_codes', [])) or 'none'}"
        )

    mismatch_counts = dict(reconciliation.get("mismatch_counts") or {})
    for code in sorted(mismatch_counts):
        print(f"{code}: {mismatch_counts[code]}")


if __name__ == "__main__":
    main()
