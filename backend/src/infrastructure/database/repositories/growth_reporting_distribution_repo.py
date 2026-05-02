from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_reporting_delivery_model import GrowthReportingDeliveryModel
from src.infrastructure.database.models.growth_reporting_subscription_model import (
    GrowthReportingSubscriptionModel,
)


@dataclass(frozen=True)
class GrowthReportingSubscriptionWrite:
    recipient_email: str
    recipient_name: str | None
    audience_key: str
    delivery_channel: str
    cadence: str
    report_window_days: int
    template_key: str
    template_locale: str
    email_subject_prefix: str | None
    title_override: str | None
    recipient_domain_policy: str
    allowed_recipient_domains: list[str]
    suppressed_until: datetime | None
    suppression_reason_code: str | None
    subscription_status: str
    next_delivery_at: datetime
    created_by_admin_user_id: UUID | None
    updated_by_admin_user_id: UUID | None


@dataclass(frozen=True)
class GrowthReportingDeliveryWrite:
    subscription_id: UUID
    recipient_email: str
    recipient_name: str | None
    audience_key: str
    delivery_channel: str
    cadence: str
    report_window_days: int
    template_key: str
    template_locale: str
    subject_line: str
    title_line: str
    recipient_domain_policy: str
    allowed_recipient_domains: list[str]
    delivery_status: str
    status_reason: str | None
    window_start: date
    window_end: date
    freshness_status: str
    artifact_checksum: str | None
    artifact_payload: dict[str, Any]
    planned_at: datetime
    started_at: datetime | None
    delivered_at: datetime | None = None
    provider_name: str | None = None
    provider_message_id: str | None = None
    failure_message: str | None = None


class GrowthReportingDistributionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_subscription(
        self,
        payload: GrowthReportingSubscriptionWrite,
    ) -> GrowthReportingSubscriptionModel:
        model = GrowthReportingSubscriptionModel(
            recipient_email=payload.recipient_email,
            recipient_name=payload.recipient_name,
            audience_key=payload.audience_key,
            delivery_channel=payload.delivery_channel,
            cadence=payload.cadence,
            report_window_days=payload.report_window_days,
            template_key=payload.template_key,
            template_locale=payload.template_locale,
            email_subject_prefix=payload.email_subject_prefix,
            title_override=payload.title_override,
            recipient_domain_policy=payload.recipient_domain_policy,
            allowed_recipient_domains=list(payload.allowed_recipient_domains),
            suppressed_until=_coerce_utc(payload.suppressed_until) if payload.suppressed_until else None,
            suppression_reason_code=payload.suppression_reason_code,
            subscription_status=payload.subscription_status,
            next_delivery_at=_coerce_utc(payload.next_delivery_at),
            created_by_admin_user_id=payload.created_by_admin_user_id,
            updated_by_admin_user_id=payload.updated_by_admin_user_id,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_subscriptions(self) -> list[GrowthReportingSubscriptionModel]:
        result = await self._session.execute(
            select(GrowthReportingSubscriptionModel).order_by(
                GrowthReportingSubscriptionModel.subscription_status.asc(),
                GrowthReportingSubscriptionModel.audience_key.asc(),
                GrowthReportingSubscriptionModel.next_delivery_at.asc(),
                GrowthReportingSubscriptionModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def get_subscription(self, subscription_id: UUID) -> GrowthReportingSubscriptionModel | None:
        return await self._session.get(GrowthReportingSubscriptionModel, subscription_id)

    async def list_due_subscriptions(self, *, now: datetime, limit: int) -> list[GrowthReportingSubscriptionModel]:
        result = await self._session.execute(
            select(GrowthReportingSubscriptionModel)
            .where(GrowthReportingSubscriptionModel.subscription_status == "active")
            .where(GrowthReportingSubscriptionModel.next_delivery_at <= _coerce_utc(now))
            .order_by(
                GrowthReportingSubscriptionModel.next_delivery_at.asc(),
                GrowthReportingSubscriptionModel.created_at.asc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_delivery(self, payload: GrowthReportingDeliveryWrite) -> GrowthReportingDeliveryModel:
        model = GrowthReportingDeliveryModel(
            subscription_id=payload.subscription_id,
            recipient_email=payload.recipient_email,
            recipient_name=payload.recipient_name,
            audience_key=payload.audience_key,
            delivery_channel=payload.delivery_channel,
            cadence=payload.cadence,
            report_window_days=payload.report_window_days,
            template_key=payload.template_key,
            template_locale=payload.template_locale,
            subject_line=payload.subject_line,
            title_line=payload.title_line,
            recipient_domain_policy=payload.recipient_domain_policy,
            allowed_recipient_domains=list(payload.allowed_recipient_domains),
            delivery_status=payload.delivery_status,
            status_reason=payload.status_reason,
            window_start=payload.window_start,
            window_end=payload.window_end,
            freshness_status=payload.freshness_status,
            artifact_checksum=payload.artifact_checksum,
            artifact_payload=dict(payload.artifact_payload),
            provider_name=payload.provider_name,
            provider_message_id=payload.provider_message_id,
            failure_message=payload.failure_message,
            planned_at=_coerce_utc(payload.planned_at),
            started_at=_coerce_utc(payload.started_at) if payload.started_at else None,
            delivered_at=_coerce_utc(payload.delivered_at) if payload.delivered_at else None,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_deliveries(self, *, limit: int = 20) -> list[GrowthReportingDeliveryModel]:
        result = await self._session.execute(
            select(GrowthReportingDeliveryModel).order_by(
                GrowthReportingDeliveryModel.created_at.desc(),
                GrowthReportingDeliveryModel.planned_at.desc(),
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def get_delivery(self, delivery_id: UUID) -> GrowthReportingDeliveryModel | None:
        return await self._session.get(GrowthReportingDeliveryModel, delivery_id)

    async def delete_old_deliveries(self, *, older_than: datetime) -> int:
        result = await self._session.execute(
            delete(GrowthReportingDeliveryModel).where(
                GrowthReportingDeliveryModel.created_at < _coerce_utc(older_than),
                GrowthReportingDeliveryModel.delivery_status.in_(("delivered", "failed", "skipped")),
            )
        )
        return int(result.rowcount or 0)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
