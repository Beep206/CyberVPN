from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.enums import ServerStatus


@dataclass(frozen=True)
class Server:
    uuid: UUID
    name: str
    address: str
    port: int
    is_connected: bool
    is_disabled: bool
    is_connecting: bool
    created_at: datetime
    updated_at: datetime
    country_code: str | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    inbound_count: int | None = None
    users_online: int | None = None
    xray_version: str | None = None
    vpn_protocol: str | None = None

    @property
    def status(self) -> ServerStatus:
        if self.is_disabled:
            return ServerStatus.MAINTENANCE
        if self.is_connecting:
            return ServerStatus.WARNING
        if self.is_connected:
            return ServerStatus.ONLINE
        return ServerStatus.OFFLINE
