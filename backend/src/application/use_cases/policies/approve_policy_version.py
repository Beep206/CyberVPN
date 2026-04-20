from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.repositories.policy_version_repo import PolicyVersionRepository


class ApprovePolicyVersionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PolicyVersionRepository(session)

    async def execute(
        self,
        policy_version_id: UUID,
        *,
        approved_by_admin_user_id: UUID,
        version_status: str = "active",
        effective_from: datetime | None = None,
        effective_to: datetime | None = None,
    ) -> PolicyVersionModel:
        model = await self._repo.get_by_id(policy_version_id)
        if model is None:
            raise ValueError("Policy version not found")

        resolved_effective_from = effective_from or model.effective_from
        resolved_effective_to = effective_to if effective_to is not None else model.effective_to
        if resolved_effective_to is not None and resolved_effective_to <= resolved_effective_from:
            raise ValueError("Policy effective_to must be greater than effective_from")

        model.approval_state = "approved"
        model.version_status = version_status
        model.approved_by_admin_user_id = approved_by_admin_user_id
        model.approved_at = datetime.now(UTC)
        model.effective_from = resolved_effective_from
        model.effective_to = resolved_effective_to
        return await self._repo.update(model)
