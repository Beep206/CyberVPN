"""Abstract repository interface for system configuration."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from src.domain.entities.system_config import SystemConfig


class SystemConfigRepository(ABC):
    @abstractmethod
    async def get(self, key: str) -> SystemConfig | None: ...

    @abstractmethod
    async def get_value(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], updated_by: UUID | None = None) -> SystemConfig: ...

    @abstractmethod
    async def get_all(self) -> list[SystemConfig]: ...
