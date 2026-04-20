from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.governance_action_model import GovernanceActionModel
from src.infrastructure.database.models.risk_identifier_model import RiskIdentifierModel
from src.infrastructure.database.models.risk_link_model import RiskLinkModel
from src.infrastructure.database.models.risk_review_attachment_model import RiskReviewAttachmentModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel


class RiskSubjectGraphRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_subject(self, model: RiskSubjectModel) -> RiskSubjectModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_subject_by_id(self, risk_subject_id: UUID) -> RiskSubjectModel | None:
        return await self._session.get(RiskSubjectModel, risk_subject_id)

    async def get_subject_by_principal(
        self,
        *,
        principal_class: str,
        principal_subject: str,
        auth_realm_id: UUID | None,
    ) -> RiskSubjectModel | None:
        stmt: Select[tuple[RiskSubjectModel]] = select(RiskSubjectModel).where(
            RiskSubjectModel.principal_class == principal_class,
            RiskSubjectModel.principal_subject == principal_subject,
        )
        if auth_realm_id is None:
            stmt = stmt.where(RiskSubjectModel.auth_realm_id.is_(None))
        else:
            stmt = stmt.where(RiskSubjectModel.auth_realm_id == auth_realm_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_subjects_by_principal(
        self,
        *,
        principal_class: str,
        principal_subject: str,
    ) -> list[RiskSubjectModel]:
        result = await self._session.execute(
            select(RiskSubjectModel)
            .where(
                RiskSubjectModel.principal_class == principal_class,
                RiskSubjectModel.principal_subject == principal_subject,
            )
            .order_by(
                RiskSubjectModel.created_at.asc(),
                RiskSubjectModel.auth_realm_id.asc().nullsfirst(),
            )
        )
        return list(result.scalars().all())

    async def create_identifier(self, model: RiskIdentifierModel) -> RiskIdentifierModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_identifiers_for_subject(self, risk_subject_id: UUID) -> list[RiskIdentifierModel]:
        result = await self._session.execute(
            select(RiskIdentifierModel)
            .where(RiskIdentifierModel.risk_subject_id == risk_subject_id)
            .order_by(RiskIdentifierModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_matching_identifiers(
        self,
        *,
        identifier_type: str,
        value_hash: str,
    ) -> list[RiskIdentifierModel]:
        result = await self._session.execute(
            select(RiskIdentifierModel)
            .where(
                RiskIdentifierModel.identifier_type == identifier_type,
                RiskIdentifierModel.value_hash == value_hash,
            )
            .order_by(RiskIdentifierModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_link_between_subjects(
        self,
        *,
        left_subject_id: UUID,
        right_subject_id: UUID,
        identifier_type: str,
    ) -> RiskLinkModel | None:
        result = await self._session.execute(
            select(RiskLinkModel).where(
                RiskLinkModel.left_subject_id == left_subject_id,
                RiskLinkModel.right_subject_id == right_subject_id,
                RiskLinkModel.identifier_type == identifier_type,
            )
        )
        return result.scalar_one_or_none()

    async def create_link(self, model: RiskLinkModel) -> RiskLinkModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_links_for_subject(self, risk_subject_id: UUID) -> list[RiskLinkModel]:
        result = await self._session.execute(
            select(RiskLinkModel)
            .where(
                or_(
                    RiskLinkModel.left_subject_id == risk_subject_id,
                    RiskLinkModel.right_subject_id == risk_subject_id,
                )
            )
            .order_by(RiskLinkModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_review(self, model: RiskReviewModel) -> RiskReviewModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_review_by_id(self, risk_review_id: UUID) -> RiskReviewModel | None:
        return await self._session.get(RiskReviewModel, risk_review_id)

    async def list_reviews_for_subject(self, risk_subject_id: UUID) -> list[RiskReviewModel]:
        result = await self._session.execute(
            select(RiskReviewModel)
            .where(RiskReviewModel.risk_subject_id == risk_subject_id)
            .order_by(RiskReviewModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_reviews(
        self,
        *,
        status: str | None = None,
        review_type: str | None = None,
    ) -> list[RiskReviewModel]:
        stmt = select(RiskReviewModel)
        if status is not None:
            stmt = stmt.where(RiskReviewModel.status == status)
        if review_type is not None:
            stmt = stmt.where(RiskReviewModel.review_type == review_type)
        result = await self._session.execute(
            stmt.order_by(
                RiskReviewModel.created_at.desc(),
                RiskReviewModel.id.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_open_reviews_for_subject(self, risk_subject_id: UUID) -> list[RiskReviewModel]:
        result = await self._session.execute(
            select(RiskReviewModel)
            .where(
                RiskReviewModel.risk_subject_id == risk_subject_id,
                RiskReviewModel.status == "open",
            )
            .order_by(RiskReviewModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_review_attachment(
        self,
        model: RiskReviewAttachmentModel,
    ) -> RiskReviewAttachmentModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_review_attachments_for_review(
        self,
        risk_review_id: UUID,
    ) -> list[RiskReviewAttachmentModel]:
        result = await self._session.execute(
            select(RiskReviewAttachmentModel)
            .where(RiskReviewAttachmentModel.risk_review_id == risk_review_id)
            .order_by(
                RiskReviewAttachmentModel.created_at.asc(),
                RiskReviewAttachmentModel.id.asc(),
            )
        )
        return list(result.scalars().all())

    async def create_governance_action(
        self,
        model: GovernanceActionModel,
    ) -> GovernanceActionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_governance_actions(
        self,
        *,
        risk_subject_id: UUID | None = None,
        risk_review_id: UUID | None = None,
    ) -> list[GovernanceActionModel]:
        stmt = select(GovernanceActionModel)
        if risk_subject_id is not None:
            stmt = stmt.where(GovernanceActionModel.risk_subject_id == risk_subject_id)
        if risk_review_id is not None:
            stmt = stmt.where(GovernanceActionModel.risk_review_id == risk_review_id)
        result = await self._session.execute(
            stmt.order_by(
                GovernanceActionModel.created_at.desc(),
                GovernanceActionModel.id.desc(),
            )
        )
        return list(result.scalars().all())
