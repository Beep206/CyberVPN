from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


@dataclass(frozen=True)
class User:
    uuid: UUID | None
    username: str
    status: UserStatus
    short_uuid: str
    created_at: datetime
    updated_at: datetime
    remnawave_id: int | None = None
    subscription_uuid: UUID | None = None
    expire_at: datetime | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    download_bytes: int | None = None
    upload_bytes: int | None = None
    lifetime_used_traffic_bytes: int | None = None
    online_at: datetime | None = None
    sub_last_user_agent: str | None = None
    sub_revoked_at: datetime | None = None
    last_traffic_reset_at: datetime | None = None
    telegram_id: int | None = None
    email: str | None = None
    hwid_device_limit: int | None = None
    subscription_url: str | None = None
    auto_renew: bool | None = None
    traffic_limit_strategy: str | None = None
    active_internal_squad_uuids: tuple[str, ...] | None = None
    external_squad_uuid: str | None = None
    external_squad_uuid_observed: bool = False

    @property
    def data_usage(self) -> int:
        return self.used_traffic_bytes or 0

    @property
    def data_limit(self) -> int | None:
        return self.traffic_limit_bytes

    @property
    def expires_at(self) -> datetime | None:
        return self.expire_at

    @property
    def ref(self) -> RemnawaveUserRef:
        return RemnawaveUserRef(id=self.remnawave_id, legacy_uuid=self.uuid)
