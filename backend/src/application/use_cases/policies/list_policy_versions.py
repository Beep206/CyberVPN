from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.repositories.policy_version_repo import PolicyVersionRepository


class ListPolicyVersionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PolicyVersionRepository(session)

    async def execute(
        self,
        *,
        policy_family: str | None = None,
        policy_key: str | None = None,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        approval_state: str | None = None,
        include_inactive: bool = False,
        at: datetime | None = None,
    ) -> list[PolicyVersionModel]:
        return await self._repo.list_versions(
            policy_family=policy_family,
            policy_key=policy_key,
            subject_type=subject_type,
            subject_id=subject_id,
            approval_state=approval_state,
            include_inactive=include_inactive,
            at=at,
        )
