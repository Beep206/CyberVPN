"""System configuration domain entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class SystemConfig:
    key: str
    value: dict[str, Any]
    description: str | None = None
    updated_at: datetime | None = None
    updated_by: UUID | None = None
