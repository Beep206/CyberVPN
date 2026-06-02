"""Shared realtime transport contract helpers for messaging."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_sync_cursor() -> str:
    return f"sync:{datetime.now(UTC).isoformat().replace('+00:00', 'Z')}"


def build_sync_required_payload(*, reason: str) -> dict[str, Any]:
    return {
        "reason": reason,
        "sync_cursor": build_sync_cursor(),
        "recovery": "rest_sync",
    }
