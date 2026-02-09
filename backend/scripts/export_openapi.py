#!/usr/bin/env python3
"""Export the OpenAPI JSON specification from the FastAPI application.

ARCH-01.1: Generates ``docs/api/openapi.json`` with version metadata sourced
from ``src/version.py``.  The generated file should be committed so that
front-end code generators and contract-testing tools always have an
up-to-date, version-controlled copy of the API surface.

Usage:
    # From the backend/ directory (or anywhere with PYTHONPATH set)
    python scripts/export_openapi.py

    # With a custom output path
    python scripts/export_openapi.py --output /tmp/openapi.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure ``backend/`` is on sys.path so ``src.*`` imports resolve regardless
# of the current working directory.
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("export_openapi")

DEFAULT_OUTPUT = _BACKEND_ROOT / "docs" / "api" / "openapi.json"


def get_openapi_spec() -> dict:
    """Import the FastAPI app and return its OpenAPI schema dict."""
    try:
        from src.main import app
    except Exception as exc:
        logger.error("Failed to import the FastAPI app: %s", exc)
        raise SystemExit(1) from exc

    spec = app.openapi()
    return spec


def write_spec(spec: dict, output_path: Path) -> None:
    """Write the OpenAPI spec to *output_path* as pretty-printed JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("OpenAPI spec written to %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the CyberVPN OpenAPI specification.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    spec = get_openapi_spec()

    # Log version info from the spec
    info = spec.get("info", {})
    logger.info(
        "Exporting OpenAPI %s -- %s v%s",
        spec.get("openapi", "?"),
        info.get("title", "?"),
        info.get("version", "?"),
    )

    write_spec(spec, args.output)


if __name__ == "__main__":
    main()
