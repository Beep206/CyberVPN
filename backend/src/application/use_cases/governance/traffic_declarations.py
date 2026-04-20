from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import TrafficDeclarationStatus
from src.infrastructure.database.models.partner_traffic_declaration_model import (
    PartnerTrafficDeclarationModel,
)
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.partner_account_repository import (
    PartnerAccountRepository,
)


class CreateTrafficDeclarationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernanceRepository(session)
        self._partners = PartnerAccountRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        declaration_kind: str,
        scope_label: str,
        declaration_payload: dict | None = None,
        notes: list[str] | None = None,
        submitted_by_admin_user_id: UUID | None = None,
    ) -> PartnerTrafficDeclarationModel:
        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")
        normalized_kind = declaration_kind.strip()
        normalized_scope_label = scope_label.strip()
        if not normalized_kind:
            raise ValueError("declaration_kind is required")
        if not normalized_scope_label:
            raise ValueError("scope_label is required")

        model = PartnerTrafficDeclarationModel(
            partner_account_id=partner_account_id,
            declaration_kind=normalized_kind,
            declaration_status=TrafficDeclarationStatus.SUBMITTED.value,
            scope_label=normalized_scope_label,
            declaration_payload=dict(declaration_payload or {}),
            notes_payload=[item.strip() for item in list(notes or []) if item and item.strip()],
            submitted_by_admin_user_id=submitted_by_admin_user_id,
        )
        created = await self._repo.create_traffic_declaration(model)
        await self._session.commit()
        await self._session.refresh(created)
        return created


class ListTrafficDeclarationsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        declaration_kind: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerTrafficDeclarationModel]:
        return await self._repo.list_traffic_declarations(
            partner_account_id=partner_account_id,
            declaration_kind=declaration_kind,
            limit=limit,
            offset=offset,
        )


class GetTrafficDeclarationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GovernanceRepository(session)

    async def execute(
        self,
        *,
        traffic_declaration_id: UUID,
    ) -> PartnerTrafficDeclarationModel | None:
        return await self._repo.get_traffic_declaration_by_id(traffic_declaration_id)
