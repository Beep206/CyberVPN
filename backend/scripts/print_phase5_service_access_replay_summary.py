#!/usr/bin/env python3
"""Print a compact summary for a Phase 5 service-access replay pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_report(input_path: Path) -> dict:
    return json.loads(input_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a compact Phase 5 service-access replay summary.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to the replay pack JSON file.")
    args = parser.parse_args()

    report = _read_report(args.input)
    reconciliation = dict(report.get("reconciliation") or {})
    channel_parity_views = list(report.get("channel_parity_views") or [])

    print(f"status: {reconciliation.get('status', 'unknown')}")
    print(f"service identities: {report.get('input_summary', {}).get('service_identities', 0)}")
    print(f"entitlement grants: {report.get('input_summary', {}).get('entitlement_grants', 0)}")
    print(f"provisioning profiles: {report.get('input_summary', {}).get('provisioning_profiles', 0)}")
    print(f"access delivery channels: {report.get('input_summary', {}).get('access_delivery_channels', 0)}")
    print(f"channel expectations: {report.get('input_summary', {}).get('channel_expectations', 0)}")

    for view in channel_parity_views:
        mismatches = ",".join(view.get("mismatch_codes") or []) or "none"
        print(
            "parity "
            f"{view.get('parity_key')}: "
            f"service_identity={view.get('service_identity_id') or 'none'}, "
            f"grant={view.get('active_entitlement_grant_id') or 'none'}, "
            f"channel={view.get('selected_access_delivery_channel_id') or 'none'}, "
            f"mismatches={mismatches}"
        )

    mismatch_counts = dict(reconciliation.get("mismatch_counts") or {})
    for code in sorted(mismatch_counts):
        print(f"{code}: {mismatch_counts[code]}")


if __name__ == "__main__":
    main()
