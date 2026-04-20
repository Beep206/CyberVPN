from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AttributionTouchpointType
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.repositories.attribution_touchpoint_repo import AttributionTouchpointRepository
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.presentation.dependencies.auth_realms import RealmResolution


class RecordAttributionTouchpointUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._touchpoints = AttributionTouchpointRepository(session)
        self._partner_repo = PartnerRepository(session)
        self._commerce = CommerceSessionRepository(session)
        self._orders = OrderRepository(session)

    async def execute(
        self,
        *,
        current_realm: RealmResolution,
        touchpoint_type: str,
        user_id: UUID | None = None,
        storefront_id: UUID | None = None,
        quote_session_id: UUID | None = None,
        checkout_session_id: UUID | None = None,
        order_id: UUID | None = None,
        partner_code: str | None = None,
        partner_code_id: UUID | None = None,
        sale_channel: str | None = None,
        source_host: str | None = None,
        source_path: str | None = None,
        campaign_params: dict[str, Any] | None = None,
        evidence_payload: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
        commit: bool = True,
    ) -> AttributionTouchpointModel:
        if touchpoint_type not in {member.value for member in AttributionTouchpointType}:
            raise ValueError("Touchpoint type is invalid")

        resolved_user_id = user_id
        resolved_storefront_id = storefront_id

        if quote_session_id is not None:
            quote_session = await self._commerce.get_quote_session_by_id(quote_session_id)
            if quote_session is None:
                raise ValueError("Quote session not found")
            if str(quote_session.auth_realm_id) != current_realm.realm_id:
                raise ValueError("Quote session does not belong to the current auth realm")
            if user_id is not None and quote_session.user_id != user_id:
                raise ValueError("Quote session does not belong to the current user")
            resolved_user_id = quote_session.user_id
            resolved_storefront_id = quote_session.storefront_id

        if order_id is not None:
            order = await self._orders.get_by_id(order_id)
            if order is None:
                raise ValueError("Order not found")
            if str(order.auth_realm_id) != current_realm.realm_id:
                raise ValueError("Order does not belong to the current auth realm")
            if user_id is not None and order.user_id != user_id:
                raise ValueError("Order does not belong to the current user")
            resolved_user_id = order.user_id
            resolved_storefront_id = order.storefront_id

        resolved_partner_code_id = partner_code_id
        normalized_partner_code = partner_code.strip() if partner_code else None
        if normalized_partner_code and resolved_partner_code_id is None:
            code_model = await self._partner_repo.get_active_code_by_code(normalized_partner_code)
            if code_model is None:
                raise ValueError("Partner code not found or inactive")
            resolved_partner_code_id = code_model.id

        payload = dict(evidence_payload or {})
        if normalized_partner_code is not None:
            payload.setdefault("partner_code", normalized_partner_code)

        model = AttributionTouchpointModel(
            touchpoint_type=touchpoint_type,
            user_id=resolved_user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            storefront_id=resolved_storefront_id,
            quote_session_id=quote_session_id,
            checkout_session_id=checkout_session_id,
            order_id=order_id,
            partner_code_id=resolved_partner_code_id,
            sale_channel=sale_channel,
            source_host=source_host,
            source_path=source_path,
            campaign_params=dict(campaign_params or {}),
            evidence_payload=payload,
            occurred_at=_normalize_occurred_at(occurred_at),
        )
        created = await self._touchpoints.create(model)
        if commit:
            await self._session.commit()
        return created


def _normalize_occurred_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
