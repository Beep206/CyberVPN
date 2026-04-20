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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic Phase 8 attribution shadow pack.")
    parser.add_argument("--input", required=True, help="Path to the input snapshot JSON.")
    parser.add_argument("--output", required=True, help="Path to the output report JSON.")
    return parser.parse_args()


def main() -> None:
    from src.application.services.phase8_attribution_shadow import build_phase8_attribution_shadow_pack

    args = _parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    snapshot = json.loads(input_path.read_text(encoding="utf-8"))
    report = build_phase8_attribution_shadow_pack(snapshot)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
