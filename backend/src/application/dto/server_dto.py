from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ServerResponseDTO:
    id: UUID
    name: str
    location: str
    ip: str
    protocol: str | None
    status: str
    load: float
    uptime: float
    clients: int
    latitude: float | None = None
    longitude: float | None = None
