from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CreativeApprovalStatus
from src.infrastructure.database.models.creative_approval_model import CreativeApprovalModel
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.partner_account_repository import (
    PartnerAccountRepository,
)

_REVIEWED_CREATIVE_STATUSES = {
    CreativeApprovalStatus.ACTION_REQUIRED.value,
    CreativeApprovalStatus.UNDER_REVIEW.value,
    CreativeApprovalStatus.COMPLETE.value,
    CreativeApprovalStatus.BLOCKED.value,
}


class CreateCreativeApprovalUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernanceRepository(session)
        self._partners = PartnerAccountRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        approval_kind: str,
        approval_status: str,
        scope_label: str,
        creative_ref: str | None = None,
        approval_payload: dict | None = None,
        notes: list[str] | None = None,
        expires_at: datetime | None = None,
        submitted_by_admin_user_id: UUID | None = None,
    ) -> CreativeApprovalModel:
        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")

        normalized_kind = approval_kind.strip()
        normalized_status = approval_status.strip()
        normalized_scope_label = scope_label.strip()
        normalized_creative_ref = creative_ref.strip() if creative_ref else None
        if not normalized_kind:
            raise ValueError("approval_kind is required")
        if not normalized_status:
            raise ValueError("approval_status is required")
        if not normalized_scope_label:
            raise ValueError("scope_label is required")

        reviewed_at = datetime.now(UTC) if normalized_status in _REVIEWED_CREATIVE_STATUSES else None
        reviewed_by_admin_user_id = (
            submitted_by_admin_user_id if normalized_status in _REVIEWED_CREATIVE_STATUSES else None
        )

        model = CreativeApprovalModel(
            partner_account_id=partner_account_id,
            approval_kind=normalized_kind,
            approval_status=normalized_status,
            scope_label=normalized_scope_label,
            creative_ref=normalized_creative_ref,
            approval_payload=dict(approval_payload or {}),
            notes_payload=[item.strip() for item in list(notes or []) if item and item.strip()],
            submitted_by_admin_user_id=submitted_by_admin_user_id,
            reviewed_by_admin_user_id=reviewed_by_admin_user_id,
            reviewed_at=reviewed_at,
            expires_at=expires_at,
        )
        created = await self._repo.create_creative_approval(model)
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListCreativeApprovalsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        approval_kind: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreativeApprovalModel]:
        return await self._repo.list_creative_approvals(
            partner_account_id=partner_account_id,
            approval_kind=approval_kind,
            limit=limit,
            offset=offset,
        )


class GetCreativeApprovalUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        creative_approval_id: UUID,
    ) -> CreativeApprovalModel | None:
        return await self._repo.get_creative_approval_by_id(creative_approval_id)
