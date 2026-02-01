from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateUserDTO:
    username: str
    password: str | None = None
    data_limit: int | None = None
    expire_at: datetime | None = None
    email: str | None = None
    telegram_id: int | None = None
    traffic_limit_bytes: int | None = None
    tag: str | None = None
    plan_id: UUID | None = None


@dataclass(frozen=True)
class UserResponseDTO:
    uuid: UUID
    username: str
    status: str
    expire_at: datetime | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    online_at: datetime | None = None
    telegram_id: int | None = None
    email: str | None = None
    created_at: datetime | None = None
