#!/usr/bin/env python3
"""Build a deterministic Phase 5 service-access replay pack from a snapshot."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import types
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _BACKEND_ROOT / "src"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
if "src" not in sys.modules:
    src_package = types.ModuleType("src")
    src_package.__file__ = str(_SRC_ROOT / "__init__.py")
    src_package.__path__ = [str(_SRC_ROOT)]
    sys.modules["src"] = src_package

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_phase5_service_access_replay_pack")

DEFAULT_OUTPUT = _BACKEND_ROOT / "docs" / "evidence" / "partner-platform" / "phase5-service-access-replay-pack.json"


def _read_snapshot(input_path: Path) -> dict:
    return json.loads(input_path.read_text(encoding="utf-8"))


def _write_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    from src.application.services.phase5_service_access_replay import build_phase5_service_access_replay_pack

    parser = argparse.ArgumentParser(description="Build the Phase 5 service-access replay pack.")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to the service-access snapshot JSON file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    snapshot = _read_snapshot(args.input)
    report = build_phase5_service_access_replay_pack(snapshot)
    _write_report(report, args.output)
    logger.info("Phase 5 service-access replay pack written to %s", args.output)


if __name__ == "__main__":
    main()
