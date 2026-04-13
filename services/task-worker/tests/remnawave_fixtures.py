"""Canonical Remnawave 2.7.4 test fixtures for task-worker consumers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "remnawave"


def load_remnawave_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture by filename from the Remnawave fixture directory."""

    return json.loads((_FIXTURES_ROOT / name).read_text(encoding="utf-8"))
