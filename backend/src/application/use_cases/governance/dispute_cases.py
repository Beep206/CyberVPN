from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import DisputeCaseStatus
from src.infrastructure.database.models.dispute_case_model import DisputeCaseModel
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.partner_account_repository import (
    PartnerAccountRepository,
)
from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository

_CLOSED_DISPUTE_CASE_STATUSES = {
    DisputeCaseStatus.RESOLVED.value,
    DisputeCaseStatus.CLOSED.value,
}


class CreateDisputeCaseUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernanceRepository(session)
        self._partners = PartnerAccountRepository(session)
        self._payment_disputes = PaymentDisputeRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        payment_dispute_id: UUID | None,
        order_id: UUID | None,
        case_kind: str,
        case_status: str,
        summary: str,
        case_payload: dict | None = None,
        notes: list[str] | None = None,
        opened_by_admin_user_id: UUID | None = None,
        assigned_to_admin_user_id: UUID | None = None,
    ) -> DisputeCaseModel:
        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")

        linked_order_id = order_id
        if payment_dispute_id is not None:
            payment_dispute = await self._payment_disputes.get_by_id(payment_dispute_id)
            if payment_dispute is None:
                raise ValueError("Payment dispute not found")
            if linked_order_id is None:
                linked_order_id = payment_dispute.order_id

        normalized_kind = case_kind.strip()
        normalized_status = case_status.strip()
        normalized_summary = summary.strip()
        if not normalized_kind:
            raise ValueError("case_kind is required")
        if not normalized_status:
            raise ValueError("case_status is required")
        if not normalized_summary:
            raise ValueError("summary is required")

        closed_at = datetime.now(UTC) if normalized_status in _CLOSED_DISPUTE_CASE_STATUSES else None
        closed_by_admin_user_id = opened_by_admin_user_id if closed_at is not None else None

        model = DisputeCaseModel(
            partner_account_id=partner_account_id,
            payment_dispute_id=payment_dispute_id,
            order_id=linked_order_id,
            case_kind=normalized_kind,
            case_status=normalized_status,
            summary=normalized_summary,
            case_payload=dict(case_payload or {}),
            notes_payload=[item.strip() for item in list(notes or []) if item and item.strip()],
            opened_by_admin_user_id=opened_by_admin_user_id,
            assigned_to_admin_user_id=assigned_to_admin_user_id,
            closed_by_admin_user_id=closed_by_admin_user_id,
            closed_at=closed_at,
        )
        created = await self._repo.create_dispute_case(model)
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListDisputeCasesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        payment_dispute_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DisputeCaseModel]:
        return await self._repo.list_dispute_cases(
            partner_account_id=partner_account_id,
            payment_dispute_id=payment_dispute_id,
            limit=limit,
            offset=offset,
        )


class GetDisputeCaseUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        dispute_case_id: UUID,
    ) -> DisputeCaseModel | None:
        return await self._repo.get_dispute_case_by_id(dispute_case_id)
