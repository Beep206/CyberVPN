from __future__ import annotations

from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
    GrowthCodeReservationModel,
    GrowthCodeResolutionEventModel,
    GrowthCodeTouchpointModel,
    GrowthSignupAttributionModel,
    InviteCodePolicyModel,
    PromoCodePolicyModel,
    ReferralProgramPolicyModel,
)


class GrowthCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_code(self, model: GrowthCodeModel) -> GrowthCodeModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_code_by_id(self, growth_code_id: UUID) -> GrowthCodeModel | None:
        return await self._session.get(GrowthCodeModel, growth_code_id)

    async def get_code_by_hash(self, code_hash: str, *, code_type: str | None = None) -> GrowthCodeModel | None:
        stmt = select(GrowthCodeModel).where(GrowthCodeModel.code_hash == code_hash)
        if code_type is not None:
            stmt = stmt.where(GrowthCodeModel.code_type == code_type)
        result = await self._session.execute(stmt.limit(1))
        return result.scalars().first()

    async def list_codes(
        self,
        *,
        code_type: str | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
        owner_partner_account_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GrowthCodeModel]:
        stmt = select(GrowthCodeModel).order_by(
            GrowthCodeModel.created_at.desc(),
            GrowthCodeModel.updated_at.desc(),
        )
        if code_type is not None:
            stmt = stmt.where(GrowthCodeModel.code_type == code_type)
        if status is not None:
            stmt = stmt.where(GrowthCodeModel.status == status)
        if owner_user_id is not None:
            stmt = stmt.where(GrowthCodeModel.owner_user_id == owner_user_id)
        if owner_partner_account_id is not None:
            stmt = stmt.where(GrowthCodeModel.owner_partner_account_id == owner_partner_account_id)
        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_codes(
        self,
        *,
        code_type: str | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
        owner_partner_account_id: UUID | None = None,
    ) -> int:
        stmt = select(func.count(GrowthCodeModel.id))
        if code_type is not None:
            stmt = stmt.where(GrowthCodeModel.code_type == code_type)
        if status is not None:
            stmt = stmt.where(GrowthCodeModel.status == status)
        if owner_user_id is not None:
            stmt = stmt.where(GrowthCodeModel.owner_user_id == owner_user_id)
        if owner_partner_account_id is not None:
            stmt = stmt.where(GrowthCodeModel.owner_partner_account_id == owner_partner_account_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def create_issuance(self, model: GrowthCodeIssuanceModel) -> GrowthCodeIssuanceModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_issuances(self, growth_code_id: UUID) -> list[GrowthCodeIssuanceModel]:
        result = await self._session.execute(
            select(GrowthCodeIssuanceModel)
            .where(GrowthCodeIssuanceModel.growth_code_id == growth_code_id)
            .order_by(GrowthCodeIssuanceModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_code_by_source_payment_id(
        self,
        *,
        source_payment_id: UUID,
        code_type: str | None = None,
    ) -> GrowthCodeModel | None:
        stmt = (
            select(GrowthCodeModel)
            .join(
                GrowthCodeIssuanceModel,
                GrowthCodeIssuanceModel.growth_code_id == GrowthCodeModel.id,
            )
            .where(GrowthCodeIssuanceModel.source_payment_id == source_payment_id)
            .order_by(GrowthCodeIssuanceModel.created_at.desc())
        )
        if code_type is not None:
            stmt = stmt.where(GrowthCodeModel.code_type == code_type)
        result = await self._session.execute(stmt.limit(1))
        return result.scalars().first()

    async def create_touchpoint(self, model: GrowthCodeTouchpointModel) -> GrowthCodeTouchpointModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_touchpoint_by_id(self, touchpoint_id: UUID) -> GrowthCodeTouchpointModel | None:
        return await self._session.get(GrowthCodeTouchpointModel, touchpoint_id)

    async def list_touchpoints(self, growth_code_id: UUID) -> list[GrowthCodeTouchpointModel]:
        result = await self._session.execute(
            select(GrowthCodeTouchpointModel)
            .where(GrowthCodeTouchpointModel.growth_code_id == growth_code_id)
            .order_by(GrowthCodeTouchpointModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_signup_attribution(
        self,
        model: GrowthSignupAttributionModel,
    ) -> GrowthSignupAttributionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_signup_attributions(self, growth_code_id: UUID) -> list[GrowthSignupAttributionModel]:
        result = await self._session.execute(
            select(GrowthSignupAttributionModel)
            .where(GrowthSignupAttributionModel.growth_code_id == growth_code_id)
            .order_by(GrowthSignupAttributionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_invite_policy(self, model: InviteCodePolicyModel) -> InviteCodePolicyModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_invite_policy(self, growth_code_id: UUID) -> InviteCodePolicyModel | None:
        result = await self._session.execute(
            select(InviteCodePolicyModel).where(InviteCodePolicyModel.growth_code_id == growth_code_id).limit(1)
        )
        return result.scalars().first()

    async def create_referral_policy(self, model: ReferralProgramPolicyModel) -> ReferralProgramPolicyModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_referral_policy(self, growth_code_id: UUID) -> ReferralProgramPolicyModel | None:
        result = await self._session.execute(
            select(ReferralProgramPolicyModel)
            .where(ReferralProgramPolicyModel.growth_code_id == growth_code_id)
            .limit(1)
        )
        return result.scalars().first()

    async def create_promo_policy(self, model: PromoCodePolicyModel) -> PromoCodePolicyModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_promo_policy(self, growth_code_id: UUID) -> PromoCodePolicyModel | None:
        result = await self._session.execute(
            select(PromoCodePolicyModel).where(PromoCodePolicyModel.growth_code_id == growth_code_id).limit(1)
        )
        return result.scalars().first()

    async def create_gift_policy(self, model: GiftCodePolicyModel) -> GiftCodePolicyModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_gift_policy(self, growth_code_id: UUID) -> GiftCodePolicyModel | None:
        result = await self._session.execute(
            select(GiftCodePolicyModel).where(GiftCodePolicyModel.growth_code_id == growth_code_id).limit(1)
        )
        return result.scalars().first()

    async def list_gift_policies_for_codes(
        self,
        growth_code_ids: list[UUID],
    ) -> dict[UUID, GiftCodePolicyModel]:
        if not growth_code_ids:
            return {}
        result = await self._session.execute(
            select(GiftCodePolicyModel).where(GiftCodePolicyModel.growth_code_id.in_(growth_code_ids))
        )
        return {
            item.growth_code_id: item
            for item in result.scalars().all()
        }

    async def create_resolution_event(
        self,
        model: GrowthCodeResolutionEventModel,
    ) -> GrowthCodeResolutionEventModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_resolution_events(
        self,
        *,
        growth_code_id: UUID | None = None,
        raw_code_hash: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GrowthCodeResolutionEventModel]:
        stmt = select(GrowthCodeResolutionEventModel).order_by(GrowthCodeResolutionEventModel.created_at.desc())
        if growth_code_id is not None:
            stmt = stmt.where(GrowthCodeResolutionEventModel.growth_code_id == growth_code_id)
        if raw_code_hash is not None:
            stmt = stmt.where(GrowthCodeResolutionEventModel.raw_code_hash == raw_code_hash)
        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def create_reservation(self, model: GrowthCodeReservationModel) -> GrowthCodeReservationModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_reservation_by_id(self, reservation_id: UUID) -> GrowthCodeReservationModel | None:
        return await self._session.get(GrowthCodeReservationModel, reservation_id)

    async def list_reservations(self, growth_code_id: UUID) -> list[GrowthCodeReservationModel]:
        result = await self._session.execute(
            select(GrowthCodeReservationModel)
            .where(GrowthCodeReservationModel.growth_code_id == growth_code_id)
            .order_by(GrowthCodeReservationModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_quote_reservation(
        self,
        *,
        growth_code_id: UUID,
        quote_session_id: UUID,
        user_id: UUID,
        status: str = "reserved",
    ) -> GrowthCodeReservationModel | None:
        result = await self._session.execute(
            select(GrowthCodeReservationModel)
            .where(
                GrowthCodeReservationModel.growth_code_id == growth_code_id,
                GrowthCodeReservationModel.quote_session_id == quote_session_id,
                GrowthCodeReservationModel.user_id == user_id,
                GrowthCodeReservationModel.status == status,
            )
            .limit(1)
        )
        return result.scalars().first()

    async def list_reservations_for_quote_session(
        self,
        quote_session_id: UUID,
    ) -> list[GrowthCodeReservationModel]:
        result = await self._session.execute(
            select(GrowthCodeReservationModel)
            .where(GrowthCodeReservationModel.quote_session_id == quote_session_id)
            .order_by(GrowthCodeReservationModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_redemption(self, model: GrowthCodeRedemptionModel) -> GrowthCodeRedemptionModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_redemption_by_id(self, redemption_id: UUID) -> GrowthCodeRedemptionModel | None:
        return await self._session.get(GrowthCodeRedemptionModel, redemption_id)

    async def list_redemptions(self, growth_code_id: UUID) -> list[GrowthCodeRedemptionModel]:
        result = await self._session.execute(
            select(GrowthCodeRedemptionModel)
            .where(GrowthCodeRedemptionModel.growth_code_id == growth_code_id)
            .order_by(GrowthCodeRedemptionModel.redeemed_at.desc(), GrowthCodeRedemptionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_redemptions_for_codes(
        self,
        growth_code_ids: list[UUID],
    ) -> dict[UUID, int]:
        if not growth_code_ids:
            return {}
        result = await self._session.execute(
            select(
                GrowthCodeRedemptionModel.growth_code_id,
                func.count(GrowthCodeRedemptionModel.id),
            )
            .where(GrowthCodeRedemptionModel.growth_code_id.in_(growth_code_ids))
            .group_by(GrowthCodeRedemptionModel.growth_code_id)
        )
        return {
            growth_code_id: int(count)
            for growth_code_id, count in result.all()
        }

    async def summarize_codes_by_type_status(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthCodeModel.code_type,
                GrowthCodeModel.status,
                func.count(GrowthCodeModel.id),
            )
            .group_by(GrowthCodeModel.code_type, GrowthCodeModel.status)
            .order_by(GrowthCodeModel.code_type.asc(), GrowthCodeModel.status.asc())
        )
        return [
            {
                "code_type": code_type,
                "status": status,
                "count": int(count),
            }
            for code_type, status, count in result.all()
        ]

    async def summarize_resolution_results(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthCodeResolutionEventModel.result,
                func.count(GrowthCodeResolutionEventModel.id),
            )
            .group_by(GrowthCodeResolutionEventModel.result)
            .order_by(GrowthCodeResolutionEventModel.result.asc())
        )
        return [
            {"result": result_key, "count": int(count)}
            for result_key, count in result.all()
        ]

    async def summarize_resolution_rejections(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthCodeResolutionEventModel.reject_reason,
                func.count(GrowthCodeResolutionEventModel.id),
            )
            .where(GrowthCodeResolutionEventModel.reject_reason.is_not(None))
            .group_by(GrowthCodeResolutionEventModel.reject_reason)
            .order_by(func.count(GrowthCodeResolutionEventModel.id).desc())
        )
        return [
            {"reject_reason": reject_reason, "count": int(count)}
            for reject_reason, count in result.all()
        ]

    async def summarize_redemptions_by_code_type(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthCodeRedemptionModel.code_type,
                func.count(GrowthCodeRedemptionModel.id),
            )
            .group_by(GrowthCodeRedemptionModel.code_type)
            .order_by(GrowthCodeRedemptionModel.code_type.asc())
        )
        return [
            {"code_type": code_type, "count": int(count)}
            for code_type, count in result.all()
        ]

    async def count_active_reservations(self) -> int:
        result = await self._session.execute(
            select(func.count(GrowthCodeReservationModel.id)).where(
                GrowthCodeReservationModel.status == "reserved"
            )
        )
        return int(result.scalar_one())

    async def list_resolution_abuse_signals(
        self,
        *,
        limit: int = 50,
        min_attempts: int = 3,
    ) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(
                GrowthCodeResolutionEventModel.raw_code_hash,
                GrowthCodeResolutionEventModel.code_type,
                GrowthCodeResolutionEventModel.reject_reason,
                func.count(GrowthCodeResolutionEventModel.id),
                func.count(distinct(GrowthCodeResolutionEventModel.user_id)),
                func.max(GrowthCodeResolutionEventModel.created_at),
            )
            .where(
                GrowthCodeResolutionEventModel.reject_reason.is_not(None),
                GrowthCodeResolutionEventModel.result.in_(("rejected", "conflicted", "blocked_by_risk")),
            )
            .group_by(
                GrowthCodeResolutionEventModel.raw_code_hash,
                GrowthCodeResolutionEventModel.code_type,
                GrowthCodeResolutionEventModel.reject_reason,
            )
            .having(func.count(GrowthCodeResolutionEventModel.id) >= min_attempts)
            .order_by(
                func.max(GrowthCodeResolutionEventModel.created_at).desc(),
                func.count(GrowthCodeResolutionEventModel.id).desc(),
            )
            .limit(limit)
        )
        return [
            {
                "raw_code_hash": raw_code_hash,
                "code_type": code_type,
                "reject_reason": reject_reason,
                "attempt_count": int(attempt_count),
                "unique_users": int(unique_users or 0),
                "latest_event_at": latest_event_at,
            }
            for raw_code_hash, code_type, reject_reason, attempt_count, unique_users, latest_event_at in result.all()
        ]
