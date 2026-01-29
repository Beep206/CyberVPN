from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.server import Server


class ServerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Server | None: ...

    @abstractmethod
    async def get_all(self) -> list[Server]: ...

    @abstractmethod
    async def get_by_country(self, country_code: str) -> list[Server]: ...

    @abstractmethod
    async def create(self, server: Server) -> Server: ...

    @abstractmethod
    async def update(self, server: Server) -> Server: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
