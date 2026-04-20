#!/usr/bin/env python3
"""Print a compact summary for a generated Phase 2 reconciliation pack."""

from __future__ import annotations

import argparse
import json
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


def main() -> None:
    from src.application.services.phase2_reconciliation import summarize_phase2_reconciliation_pack

    parser = argparse.ArgumentParser(description="Print a compact summary for a Phase 2 reconciliation pack.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to a generated reconciliation pack.")
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    print(summarize_phase2_reconciliation_pack(report))


if __name__ == "__main__":
    main()
