from dataclasses import dataclass
from uuid import UUID

from src.domain.enums import TemplateType


@dataclass(frozen=True)
class SubscriptionTemplate:
    uuid: UUID
    name: str
    template_type: TemplateType
    content: str
    is_default: bool


@dataclass(frozen=True)
class SubscriptionConfig:
    user_uuid: UUID
    template_uuid: UUID
    generated_config: str
    client_type: str
