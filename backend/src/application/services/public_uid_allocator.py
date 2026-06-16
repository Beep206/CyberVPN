"""Public UID allocation helpers."""

from __future__ import annotations

from typing import Protocol

from src.domain.value_objects import public_uid

PUBLIC_UID_MAX_ATTEMPTS = 25


class PublicUIDCollisionExhaustedError(RuntimeError):
    """Raised when public UID allocation cannot find a free candidate."""


class PublicUIDLookupRepository(Protocol):
    """Repository capability required by the public UID allocator."""

    async def get_by_public_uid(self, public_uid: int) -> object | None:
        """Return an existing record for a public UID, if any."""


async def allocate_public_uid(
    repository: PublicUIDLookupRepository,
    *,
    max_attempts: int = PUBLIC_UID_MAX_ATTEMPTS,
) -> int:
    """Allocate an unused random public UID with bounded collision retry."""
    for _attempt in range(max_attempts):
        candidate = public_uid.generate_public_uid_candidate()
        if await repository.get_by_public_uid(candidate) is None:
            return candidate

    raise PublicUIDCollisionExhaustedError("Unable to allocate a unique public UID")
