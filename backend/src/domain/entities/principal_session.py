"""Principal session entity for realm-aware token/session tracking."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PrincipalSession:
    id: UUID
    auth_realm_id: UUID
    principal_subject: str
    principal_class: str
    audience: str
    scope_family: str
    access_token_jti: str | None
    refresh_token_id: UUID | None
    status: str
    issued_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
