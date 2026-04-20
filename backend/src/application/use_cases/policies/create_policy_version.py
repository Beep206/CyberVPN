from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.repositories.policy_version_repo import PolicyVersionRepository


class CreatePolicyVersionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PolicyVersionRepository(session)

    async def execute(
        self,
        *,
        policy_family: str,
        policy_key: str,
        subject_type: str,
        subject_id: UUID | None,
        version_number: int,
        payload: dict,
        approval_state: str,
        version_status: str,
        effective_from: datetime | None,
        effective_to: datetime | None,
        rejection_reason: str | None,
        supersedes_policy_version_id: UUID | None,
        created_by_admin_user_id: UUID,
    ) -> PolicyVersionModel:
        resolved_effective_from = effective_from or datetime.now(UTC)
        if effective_to is not None and effective_to <= resolved_effective_from:
            raise ValueError("Policy effective_to must be greater than effective_from")
        if version_status == "active" and approval_state != "approved":
            raise ValueError("Active policy versions must be approved")

        approved_by_admin_user_id: UUID | None = None
        approved_at: datetime | None = None
        if approval_state == "approved":
            approved_by_admin_user_id = created_by_admin_user_id
            approved_at = datetime.now(UTC)

        if supersedes_policy_version_id is not None:
            existing = await self._repo.get_by_id(supersedes_policy_version_id)
            if existing is None:
                raise ValueError("Superseded policy version not found")

        model = PolicyVersionModel(
            policy_family=policy_family.strip(),
            policy_key=policy_key.strip(),
            subject_type=subject_type.strip(),
            subject_id=subject_id,
            version_number=version_number,
            payload=payload,
            approval_state=approval_state,
            version_status=version_status,
            effective_from=resolved_effective_from,
            effective_to=effective_to,
            created_by_admin_user_id=created_by_admin_user_id,
            approved_by_admin_user_id=approved_by_admin_user_id,
            approved_at=approved_at,
            rejection_reason=rejection_reason,
            supersedes_policy_version_id=supersedes_policy_version_id,
        )
        return await self._repo.create(model)
