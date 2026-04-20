#!/usr/bin/env python3
"""Print a compact summary for a Phase 3 explainability replay pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_report(input_path: Path) -> dict:
    return json.loads(input_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a compact Phase 3 explainability replay summary.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to the replay pack JSON file.")
    args = parser.parse_args()

    report = _read_report(args.input)
    comparison = report.get("comparison", {})
    print(f"status: {comparison.get('status', 'unknown')}")
    print(f"orders: {report.get('input_summary', {}).get('orders', 0)}")
    print(f"touchpoints: {report.get('input_summary', {}).get('touchpoints', 0)}")
    print(f"growth_reward_allocations: {report.get('input_summary', {}).get('growth_reward_allocations', 0)}")
    for code, count in sorted((comparison.get("mismatch_counts") or {}).items()):
        print(f"{code}: {count}")


if __name__ == "__main__":
    main()
