"""Dual-compatible Remnawave user identity used during the 2.8 -> 3.x cutover."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RemnawaveUserRef:
    """Canonical numeric user id plus the read-only 2.8 UUID rollback reference.

    Remnawave 3 removed the user UUID from its contract.  CyberVPN keeps the
    UUID for one rollback release, but production 3.x calls must use ``id``.
    """

    id: int | None = None
    legacy_uuid: UUID | None = None

    def __post_init__(self) -> None:
        if self.id is None and self.legacy_uuid is None:
            raise ValueError("Remnawave user reference requires id or legacy_uuid")
        if self.id is not None and (isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0):
            raise ValueError("Remnawave numeric user id must be positive")

    @property
    def canonical(self) -> int:
        """Return the 3.x canonical id and fail closed before reconciliation."""

        return self.require_numeric_id()

    @property
    def rollback_identifier(self) -> int | UUID:
        """Return a legacy-capable identifier only for an explicit rollback adapter."""

        if self.id is not None:
            return self.id
        if self.legacy_uuid is None:  # defensive; __post_init__ enforces this invariant
            raise ValueError("Remnawave rollback reference is unavailable")
        return self.legacy_uuid

    @property
    def is_reconciled(self) -> bool:
        return self.id is not None

    def require_numeric_id(self) -> int:
        if self.id is None:
            raise ValueError("Remnawave numeric user id has not been reconciled")
        return self.id
