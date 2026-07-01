"""Read-only VPN balancer recommendation helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_recommendation_hash(scope: str, payload: dict[str, Any]) -> str:
    normalized = json.dumps(
        {"scope": scope, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def recommendation_key(scope: str, recommendation_hash: str) -> str:
    return f"vpn-balancer:{scope}:{recommendation_hash[:24]}"
