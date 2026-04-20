from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.policy_version import PolicyVersion


class PolicyVersionRepository(ABC):
    @abstractmethod
    async def create(self, policy_version: PolicyVersion) -> PolicyVersion: ...

    @abstractmethod
    async def list_versions(
        self,
        *,
        policy_family: str | None = None,
        policy_key: str | None = None,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        approval_state: str | None = None,
        include_inactive: bool = False,
        at: datetime | None = None,
    ) -> list[PolicyVersion]: ...

    @abstractmethod
    async def get_by_id(self, policy_version_id: UUID) -> PolicyVersion | None: ...
