from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.creative_approval_model import CreativeApprovalModel
from src.infrastructure.database.models.dispute_case_model import DisputeCaseModel
from src.infrastructure.database.models.partner_traffic_declaration_model import PartnerTrafficDeclarationModel
from src.infrastructure.database.models.partner_workspace_workflow_event_model import (
    PartnerWorkspaceWorkflowEventModel,
)


class GovernanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_traffic_declaration(
        self,
        model: PartnerTrafficDeclarationModel,
    ) -> PartnerTrafficDeclarationModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_traffic_declaration_by_id(
        self,
        traffic_declaration_id: UUID,
    ) -> PartnerTrafficDeclarationModel | None:
        return await self._session.get(PartnerTrafficDeclarationModel, traffic_declaration_id)

    async def list_traffic_declarations(
        self,
        *,
        partner_account_id: UUID | None = None,
        declaration_kind: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerTrafficDeclarationModel]:
        query = select(PartnerTrafficDeclarationModel).order_by(
            PartnerTrafficDeclarationModel.updated_at.desc(),
            PartnerTrafficDeclarationModel.created_at.desc(),
        )
        if partner_account_id is not None:
            query = query.where(PartnerTrafficDeclarationModel.partner_account_id == partner_account_id)
        if declaration_kind is not None:
            query = query.where(PartnerTrafficDeclarationModel.declaration_kind == declaration_kind)
        result = await self._session.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def create_creative_approval(self, model: CreativeApprovalModel) -> CreativeApprovalModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_creative_approval_by_id(self, creative_approval_id: UUID) -> CreativeApprovalModel | None:
        return await self._session.get(CreativeApprovalModel, creative_approval_id)

    async def list_creative_approvals(
        self,
        *,
        partner_account_id: UUID | None = None,
        approval_kind: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreativeApprovalModel]:
        query = select(CreativeApprovalModel).order_by(
            CreativeApprovalModel.updated_at.desc(),
            CreativeApprovalModel.created_at.desc(),
        )
        if partner_account_id is not None:
            query = query.where(CreativeApprovalModel.partner_account_id == partner_account_id)
        if approval_kind is not None:
            query = query.where(CreativeApprovalModel.approval_kind == approval_kind)
        result = await self._session.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def create_dispute_case(self, model: DisputeCaseModel) -> DisputeCaseModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_dispute_case_by_id(self, dispute_case_id: UUID) -> DisputeCaseModel | None:
        return await self._session.get(DisputeCaseModel, dispute_case_id)

    async def list_dispute_cases(
        self,
        *,
        partner_account_id: UUID | None = None,
        payment_dispute_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DisputeCaseModel]:
        query = select(DisputeCaseModel).order_by(
            DisputeCaseModel.updated_at.desc(),
            DisputeCaseModel.created_at.desc(),
        )
        if partner_account_id is not None:
            query = query.where(DisputeCaseModel.partner_account_id == partner_account_id)
        if payment_dispute_id is not None:
            query = query.where(DisputeCaseModel.payment_dispute_id == payment_dispute_id)
        result = await self._session.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def create_workspace_workflow_event(
        self,
        model: PartnerWorkspaceWorkflowEventModel,
    ) -> PartnerWorkspaceWorkflowEventModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_workspace_workflow_events(
        self,
        *,
        partner_account_id: UUID,
        subject_kind: str | None = None,
        subject_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PartnerWorkspaceWorkflowEventModel]:
        query = (
            select(PartnerWorkspaceWorkflowEventModel)
            .where(PartnerWorkspaceWorkflowEventModel.partner_account_id == partner_account_id)
            .order_by(
                PartnerWorkspaceWorkflowEventModel.created_at.asc(),
                PartnerWorkspaceWorkflowEventModel.id.asc(),
            )
        )
        if subject_kind is not None:
            query = query.where(PartnerWorkspaceWorkflowEventModel.subject_kind == subject_kind)
        if subject_id is not None:
            query = query.where(PartnerWorkspaceWorkflowEventModel.subject_id == subject_id)
        result = await self._session.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())
