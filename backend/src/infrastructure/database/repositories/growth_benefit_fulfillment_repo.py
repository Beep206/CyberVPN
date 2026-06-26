from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_benefits.fulfill import (
    BenefitFulfillmentRecord,
    DuplicateBenefitFulfillmentError,
    DuplicateInviteBatchError,
    InviteBatchRecord,
    InviteCodeRecord,
    NewBenefitFulfillment,
    NewInviteBatch,
    NewInviteCode,
)
from src.infrastructure.database.models.growth_benefit_model import (
    GrowthBenefitFulfillmentModel,
    InviteBatchModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel


class GrowthBenefitFulfillmentRepository:
    """SQLAlchemy adapter for Growth Codes v6 benefit fulfillment state.

    The caller owns the surrounding transaction. Methods flush so the caller can
    observe generated identifiers and database constraints before committing.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_fulfillment_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BenefitFulfillmentRecord | None:
        result = await self._session.execute(
            select(GrowthBenefitFulfillmentModel).where(
                GrowthBenefitFulfillmentModel.idempotency_key == idempotency_key
            )
        )
        model = result.scalars().first()
        return _fulfillment_record(model) if model is not None else None

    async def create_fulfillment(self, data: NewBenefitFulfillment) -> BenefitFulfillmentRecord:
        model = GrowthBenefitFulfillmentModel(
            benefit_id=data.benefit_id,
            growth_code_id=data.growth_code_id,
            user_id=data.user_id,
            order_id=data.order_id,
            payment_id=data.payment_id,
            idempotency_key=data.idempotency_key,
            status=data.status,
            attempt_count=data.attempt_count,
            config_snapshot=dict(data.config_snapshot),
            result_payload=dict(data.result_payload),
            started_at=data.started_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError as exc:
            if _is_idempotency_violation(exc):
                raise DuplicateBenefitFulfillmentError(data.idempotency_key) from exc
            raise
        await self._session.refresh(model)
        return _fulfillment_record(model)

    async def set_fulfillment_result(
        self,
        *,
        fulfillment_id: UUID,
        status: str,
        result_payload: dict[str, Any],
        completed_at: datetime | None,
    ) -> BenefitFulfillmentRecord:
        model = await self._session.get(GrowthBenefitFulfillmentModel, fulfillment_id)
        if model is None:
            raise ValueError("growth benefit fulfillment was not found")
        model.status = status
        model.result_payload = dict(result_payload)
        model.completed_at = completed_at
        model.error_code = None
        model.error_message = None
        await self._session.flush()
        await self._session.refresh(model)
        return _fulfillment_record(model)

    async def get_invite_batch_by_idempotency_key(self, idempotency_key: str) -> InviteBatchRecord | None:
        result = await self._session.execute(
            select(InviteBatchModel).where(InviteBatchModel.idempotency_key == idempotency_key)
        )
        model = result.scalars().first()
        return _invite_batch_record(model) if model is not None else None

    async def create_invite_batch(self, data: NewInviteBatch) -> InviteBatchRecord:
        model = InviteBatchModel(
            owner_user_id=data.owner_user_id,
            campaign_id=data.campaign_id,
            source_growth_code_id=data.source_growth_code_id,
            source_benefit_id=data.source_benefit_id,
            source_order_id=data.source_order_id,
            source_payment_id=data.source_payment_id,
            source_type=data.source_type,
            requested_count=data.requested_count,
            issued_count=data.issued_count,
            friend_days=data.friend_days,
            expiry_mode=data.expiry_mode,
            expiry_days=data.expiry_days,
            expires_at=data.expires_at,
            entitlement_mode=data.entitlement_mode,
            entitlement_profile_key=data.entitlement_profile_key,
            plan_id=data.plan_id,
            entitlement_snapshot=dict(data.entitlement_snapshot),
            status=data.status,
            idempotency_key=data.idempotency_key,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError as exc:
            if _is_idempotency_violation(exc):
                raise DuplicateInviteBatchError(data.idempotency_key) from exc
            raise
        await self._session.refresh(model)
        return _invite_batch_record(model)

    async def set_invite_batch_issued(
        self,
        *,
        batch_id: UUID,
        issued_count: int,
        status: str,
    ) -> InviteBatchRecord:
        model = await self._session.get(InviteBatchModel, batch_id)
        if model is None:
            raise ValueError("growth invite batch was not found")
        model.issued_count = issued_count
        model.status = status
        await self._session.flush()
        await self._session.refresh(model)
        return _invite_batch_record(model)

    async def list_invite_codes_for_batch(self, batch_id: UUID) -> tuple[InviteCodeRecord, ...]:
        result = await self._session.execute(
            select(InviteCodeModel).where(InviteCodeModel.batch_id == batch_id).order_by(InviteCodeModel.id.asc())
        )
        return tuple(_invite_code_record(model) for model in result.scalars().all())

    async def create_invite_codes(self, data: tuple[NewInviteCode, ...]) -> tuple[InviteCodeRecord, ...]:
        models = [
            InviteCodeModel(
                code=item.code,
                owner_user_id=item.owner_user_id,
                free_days=item.free_days,
                plan_id=item.plan_id,
                batch_id=item.batch_id,
                source_growth_code_id=item.source_growth_code_id,
                source_benefit_id=item.source_benefit_id,
                source_payment_id=item.source_payment_id,
                expires_at=item.expires_at,
                code_hash=item.code_hash,
                code_prefix=item.code_prefix,
                entitlement_mode=item.entitlement_mode,
                entitlement_profile_key=item.entitlement_profile_key,
                entitlement_snapshot=dict(item.entitlement_snapshot),
                source="growth_benefit",
                status="issued",
            )
            for item in data
        ]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return tuple(_invite_code_record(model) for model in models)


def _fulfillment_record(model: GrowthBenefitFulfillmentModel) -> BenefitFulfillmentRecord:
    return BenefitFulfillmentRecord(
        id=model.id,
        benefit_id=model.benefit_id,
        growth_code_id=model.growth_code_id,
        user_id=model.user_id,
        order_id=model.order_id,
        payment_id=model.payment_id,
        idempotency_key=model.idempotency_key,
        status=model.status,
        attempt_count=model.attempt_count,
        config_snapshot=dict(model.config_snapshot or {}),
        result_payload=dict(model.result_payload or {}),
        error_code=model.error_code,
        error_message=model.error_message,
        started_at=model.started_at,
        completed_at=model.completed_at,
        next_retry_at=model.next_retry_at,
    )


def _invite_batch_record(model: InviteBatchModel) -> InviteBatchRecord:
    return InviteBatchRecord(
        id=model.id,
        owner_user_id=model.owner_user_id,
        campaign_id=model.campaign_id,
        source_growth_code_id=model.source_growth_code_id,
        source_benefit_id=model.source_benefit_id,
        source_order_id=model.source_order_id,
        source_payment_id=model.source_payment_id,
        source_type=model.source_type,
        requested_count=model.requested_count,
        issued_count=model.issued_count,
        friend_days=model.friend_days,
        expiry_mode=model.expiry_mode,
        expiry_days=model.expiry_days,
        expires_at=model.expires_at,
        entitlement_mode=model.entitlement_mode,
        entitlement_profile_key=model.entitlement_profile_key,
        plan_id=model.plan_id,
        entitlement_snapshot=dict(model.entitlement_snapshot or {}),
        status=model.status,
        idempotency_key=model.idempotency_key,
    )


def _invite_code_record(model: InviteCodeModel) -> InviteCodeRecord:
    if model.batch_id is None or model.source_growth_code_id is None or model.source_benefit_id is None:
        raise ValueError("growth invite code is missing source references")
    if model.source_payment_id is None:
        raise ValueError("growth invite code is missing source payment")
    return InviteCodeRecord(
        id=model.id,
        owner_user_id=model.owner_user_id,
        batch_id=model.batch_id,
        source_growth_code_id=model.source_growth_code_id,
        source_benefit_id=model.source_benefit_id,
        source_payment_id=model.source_payment_id,
        free_days=model.free_days,
        expires_at=model.expires_at,
        code_hash=str(model.code_hash or ""),
        code_prefix=str(model.code_prefix or ""),
        status=model.status,
    )


def _is_idempotency_violation(exc: IntegrityError) -> bool:
    return "idempotency" in str(exc).lower()
