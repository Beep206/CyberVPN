"""Public account UID value object helpers."""

from __future__ import annotations

import secrets

PUBLIC_UID_MIN = 10_000_000
PUBLIC_UID_MAX = 99_999_999
PUBLIC_UID_RANGE = PUBLIC_UID_MAX - PUBLIC_UID_MIN + 1


def generate_public_uid_candidate() -> int:
    """Generate an eight-digit non-sequential public account UID candidate."""
    return PUBLIC_UID_MIN + secrets.randbelow(PUBLIC_UID_RANGE)


def is_public_uid(value: int) -> bool:
    """Return True when a value fits the public UID numeric range."""
    return PUBLIC_UID_MIN <= value <= PUBLIC_UID_MAX
