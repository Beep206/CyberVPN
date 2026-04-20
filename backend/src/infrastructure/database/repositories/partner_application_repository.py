"""Repository for partner application drafts, lanes, reviews, and attachments."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_application_model import (
    PartnerApplicationAttachmentModel,
    PartnerApplicationDraftModel,
    PartnerApplicationReviewRequestModel,
    PartnerLaneApplicationModel,
)


class PartnerApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current_draft_for_applicant(
        self,
        applicant_admin_user_id: UUID,
    ) -> PartnerApplicationDraftModel | None:
        result = await self._session.execute(
            select(PartnerApplicationDraftModel).where(
                PartnerApplicationDraftModel.applicant_admin_user_id == applicant_admin_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_draft_by_id(self, draft_id: UUID) -> PartnerApplicationDraftModel | None:
        return await self._session.get(PartnerApplicationDraftModel, draft_id)

    async def get_draft_by_partner_account_id(
        self,
        partner_account_id: UUID,
    ) -> PartnerApplicationDraftModel | None:
        result = await self._session.execute(
            select(PartnerApplicationDraftModel).where(
                PartnerApplicationDraftModel.partner_account_id == partner_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_drafts(self) -> list[PartnerApplicationDraftModel]:
        result = await self._session.execute(
            select(PartnerApplicationDraftModel).order_by(
                PartnerApplicationDraftModel.updated_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def create_draft(
        self,
        model: PartnerApplicationDraftModel,
    ) -> PartnerApplicationDraftModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_draft(
        self,
        model: PartnerApplicationDraftModel,
    ) -> PartnerApplicationDraftModel:
        await self._session.flush()
        return model

    async def list_lane_applications(
        self,
        partner_account_id: UUID,
    ) -> list[PartnerLaneApplicationModel]:
        result = await self._session.execute(
            select(PartnerLaneApplicationModel)
            .where(PartnerLaneApplicationModel.partner_account_id == partner_account_id)
            .order_by(PartnerLaneApplicationModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_lane_application_by_id(
        self,
        lane_application_id: UUID,
    ) -> PartnerLaneApplicationModel | None:
        return await self._session.get(PartnerLaneApplicationModel, lane_application_id)

    async def get_lane_application_by_lane_key(
        self,
        *,
        partner_account_id: UUID,
        lane_key: str,
    ) -> PartnerLaneApplicationModel | None:
        result = await self._session.execute(
            select(PartnerLaneApplicationModel).where(
                PartnerLaneApplicationModel.partner_account_id == partner_account_id,
                PartnerLaneApplicationModel.lane_key == lane_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_lane_application(
        self,
        model: PartnerLaneApplicationModel,
    ) -> PartnerLaneApplicationModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_lane_application(
        self,
        model: PartnerLaneApplicationModel,
    ) -> PartnerLaneApplicationModel:
        await self._session.flush()
        return model

    async def delete_lane_applications_except(
        self,
        *,
        partner_account_id: UUID,
        keep_lane_keys: set[str],
    ) -> None:
        statement = delete(PartnerLaneApplicationModel).where(
            PartnerLaneApplicationModel.partner_account_id == partner_account_id,
        )
        if keep_lane_keys:
            statement = statement.where(
                PartnerLaneApplicationModel.lane_key.not_in(keep_lane_keys),
            )
        await self._session.execute(statement)

    async def list_review_requests(
        self,
        partner_account_id: UUID,
    ) -> list[PartnerApplicationReviewRequestModel]:
        result = await self._session.execute(
            select(PartnerApplicationReviewRequestModel)
            .where(PartnerApplicationReviewRequestModel.partner_account_id == partner_account_id)
            .order_by(
                PartnerApplicationReviewRequestModel.requested_at.desc(),
                PartnerApplicationReviewRequestModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def get_review_request_by_id(
        self,
        review_request_id: UUID,
    ) -> PartnerApplicationReviewRequestModel | None:
        return await self._session.get(PartnerApplicationReviewRequestModel, review_request_id)

    async def create_review_request(
        self,
        model: PartnerApplicationReviewRequestModel,
    ) -> PartnerApplicationReviewRequestModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_review_request(
        self,
        model: PartnerApplicationReviewRequestModel,
    ) -> PartnerApplicationReviewRequestModel:
        await self._session.flush()
        return model

    async def list_attachments(
        self,
        partner_account_id: UUID,
    ) -> list[PartnerApplicationAttachmentModel]:
        result = await self._session.execute(
            select(PartnerApplicationAttachmentModel)
            .where(PartnerApplicationAttachmentModel.partner_account_id == partner_account_id)
            .order_by(PartnerApplicationAttachmentModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_attachment(
        self,
        model: PartnerApplicationAttachmentModel,
    ) -> PartnerApplicationAttachmentModel:
        self._session.add(model)
        await self._session.flush()
        return model
