from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.policy_version_model import PolicyVersionModel


class PolicyVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: PolicyVersionModel) -> PolicyVersionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def update(self, model: PolicyVersionModel) -> PolicyVersionModel:
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, policy_version_id: UUID) -> PolicyVersionModel | None:
        return await self._session.get(PolicyVersionModel, policy_version_id)

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
    ) -> list[PolicyVersionModel]:
        now = at or datetime.now(UTC)
        query: Select[tuple[PolicyVersionModel]] = select(PolicyVersionModel).order_by(
            PolicyVersionModel.policy_family.asc(),
            PolicyVersionModel.policy_key.asc(),
            PolicyVersionModel.version_number.desc(),
        )
        if policy_family is not None:
            query = query.where(PolicyVersionModel.policy_family == policy_family)
        if policy_key is not None:
            query = query.where(PolicyVersionModel.policy_key == policy_key)
        if subject_type is not None:
            query = query.where(PolicyVersionModel.subject_type == subject_type)
        if subject_id is not None:
            query = query.where(PolicyVersionModel.subject_id == subject_id)
        if approval_state is not None:
            query = query.where(PolicyVersionModel.approval_state == approval_state)
        if not include_inactive:
            query = query.where(
                PolicyVersionModel.approval_state == "approved",
                PolicyVersionModel.version_status == "active",
                PolicyVersionModel.effective_from <= now,
                (PolicyVersionModel.effective_to.is_(None)) | (PolicyVersionModel.effective_to > now),
            )
        result = await self._session.execute(query)
        return list(result.scalars().all())
