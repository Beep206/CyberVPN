from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a compact summary for a Phase 8 attribution shadow pack.")
    parser.add_argument("--input", required=True, help="Path to the generated report JSON.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    reconciliation = dict(report.get("reconciliation") or {})
    phase3_reference = dict(report.get("phase3_reference") or {})
    analytical_reference = dict(report.get("analytical_reference") or {})

    print(f"status: {reconciliation.get('status', 'unknown')}")
    print(f"phase3 reference: {phase3_reference.get('status', 'unknown')}")
    print(f"analytical reference: {analytical_reference.get('status', 'unknown')}")

    for lane_view in report.get("lane_divergence_views", []):
        print(
            "lane "
            f"{lane_view.get('lane_key')}: "
            f"rate={lane_view.get('divergence_rate')} "
            f"max={lane_view.get('max_divergence_rate')} "
            f"blocking_orders={lane_view.get('blocking_orders')} "
            f"tolerated_orders={lane_view.get('tolerated_orders')}"
        )

    mismatch_counts = reconciliation.get("mismatch_counts") or {}
    for code in sorted(mismatch_counts):
        print(f"{code}: {mismatch_counts[code]}")


if __name__ == "__main__":
    main()
