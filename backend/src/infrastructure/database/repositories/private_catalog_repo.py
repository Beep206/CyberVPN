from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_codes.namespace import NormalizedCustomerCode
from src.application.use_cases.private_catalog.preflight import (
    PrivateCatalogGrantRecord,
    PrivateCatalogRepository,
    PrivatePlanPreview,
    PrivatePolicyRecord,
    PrivateStorefrontRecord,
)
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthPrivateCatalogPolicyModel,
    PrivateCatalogAccessGrantModel,
)
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel


class SqlAlchemyPrivateCatalogRepository(PrivateCatalogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_storefront(self, storefront_key: str) -> PrivateStorefrontRecord | None:
        result = await self._session.execute(
            select(StorefrontModel).where(
                StorefrontModel.storefront_key == storefront_key,
                StorefrontModel.status == "active",
                StorefrontModel.auth_realm_id.is_not(None),
            )
        )
        model = result.scalars().first()
        if model is None or model.auth_realm_id is None:
            return None
        return PrivateStorefrontRecord(
            id=model.id,
            auth_realm_id=model.auth_realm_id,
            storefront_key=model.storefront_key,
        )

    async def get_access_grant_by_id(self, grant_id: UUID) -> PrivateCatalogAccessGrantModel | None:
        return await self._session.get(PrivateCatalogAccessGrantModel, grant_id)

    async def attach_grant_to_quote(self, *, grant_id: UUID, quote_session_id: UUID) -> PrivateCatalogAccessGrantModel:
        grant = await self._get_access_grant_for_update(grant_id)
        if grant is None:
            raise ValueError("PRIVATE_CATALOG_GRANT_INVALID")
        if grant.attached_quote_session_id == quote_session_id:
            return grant
        if grant.attached_quote_session_id is not None:
            raise ValueError("PRIVATE_CATALOG_GRANT_ALREADY_ATTACHED")
        if (
            grant.max_quote_conversions is not None
            and int(grant.quote_conversions_count or 0) >= grant.max_quote_conversions
        ):
            raise ValueError("PRIVATE_CATALOG_GRANT_EXHAUSTED")
        grant.attached_quote_session_id = quote_session_id
        grant.quote_conversions_count = int(grant.quote_conversions_count or 0) + 1
        await self._session.flush()
        return grant

    async def attach_grant_to_checkout(
        self,
        *,
        grant_id: UUID,
        checkout_session_id: UUID,
    ) -> PrivateCatalogAccessGrantModel:
        grant = await self._get_access_grant_for_update(grant_id)
        if grant is None:
            raise ValueError("PRIVATE_CATALOG_GRANT_INVALID")
        if grant.attached_checkout_session_id == checkout_session_id:
            return grant
        if grant.attached_checkout_session_id is not None:
            raise ValueError("PRIVATE_CATALOG_GRANT_ALREADY_ATTACHED")
        grant.attached_checkout_session_id = checkout_session_id
        await self._session.flush()
        return grant

    async def consume_grant_for_order(self, *, grant_id: UUID, order_id: UUID) -> PrivateCatalogAccessGrantModel:
        grant = await self._get_access_grant_for_update(grant_id)
        if grant is None:
            raise ValueError("PRIVATE_CATALOG_GRANT_INVALID")
        if grant.consumed_order_id == order_id:
            return grant
        if grant.consumed_order_id is not None:
            raise ValueError("PRIVATE_CATALOG_GRANT_ALREADY_CONSUMED")
        grant.consumed_order_id = order_id
        grant.status = "consumed"
        await self._session.flush()
        return grant

    async def _get_access_grant_for_update(self, grant_id: UUID) -> PrivateCatalogAccessGrantModel | None:
        result = await self._session.execute(
            select(PrivateCatalogAccessGrantModel)
            .where(PrivateCatalogAccessGrantModel.id == grant_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def find_active_private_policy(self, code_hash: str) -> PrivatePolicyRecord | None:
        result = await self._session.execute(
            select(GrowthPrivateCatalogPolicyModel)
            .join(GrowthCodeModel, GrowthCodeModel.id == GrowthPrivateCatalogPolicyModel.growth_code_id)
            .where(
                GrowthCodeModel.code_hash == code_hash,
                GrowthCodeModel.code_namespace == "customer_input",
                GrowthCodeModel.status == "active",
                GrowthPrivateCatalogPolicyModel.is_active.is_(True),
            )
        )
        policy = result.scalars().first()
        if policy is None:
            return None
        return PrivatePolicyRecord(
            id=policy.id,
            policy_version_id=policy.policy_version_id,
            growth_code_id=policy.growth_code_id,
            target_plan_ids=tuple(UUID(str(item)) for item in policy.target_plan_ids or ()),
            allowed_storefront_ids=tuple(UUID(str(item)) for item in policy.allowed_storefront_ids or ()),
            allowed_channels=tuple(str(item).lower() for item in policy.allowed_channels or ()),
            grant_ttl_seconds=policy.grant_ttl_seconds,
            max_quote_conversions=policy.max_quote_conversions,
            requires_auth=policy.requires_auth,
        )

    async def list_private_plan_previews(
        self,
        *,
        plan_ids: tuple[UUID, ...],
        channel: str,
        currency: str,
    ) -> tuple[PrivatePlanPreview, ...]:
        if not plan_ids:
            return ()
        result = await self._session.execute(
            select(SubscriptionPlanModel)
            .where(
                SubscriptionPlanModel.id.in_(plan_ids),
                SubscriptionPlanModel.is_active.is_(True),
                SubscriptionPlanModel.catalog_access_class == "private_code_gated",
            )
            .order_by(SubscriptionPlanModel.sort_order.asc(), SubscriptionPlanModel.id.asc())
        )
        previews: list[PrivatePlanPreview] = []
        for plan in result.scalars().all():
            sale_channels = {str(item).lower() for item in plan.sale_channels or ()}
            if sale_channels and channel not in sale_channels:
                continue
            price_value = plan.price_rub if currency == "RUB" and plan.price_rub is not None else plan.price_usd
            amount = Decimal(str(price_value))
            previews.append(
                PrivatePlanPreview(
                    plan_id=plan.id,
                    display_name=plan.display_name or plan.name,
                    plan_code=plan.plan_code or plan.name,
                    duration_days=plan.duration_days,
                    amount=amount,
                    currency=currency,
                    entitlement_summary={
                        "devices_included": plan.device_limit,
                        "traffic_limit_bytes": plan.traffic_limit_bytes,
                        "support_sla": plan.support_sla,
                    },
                )
            )
        return tuple(previews)

    async def create_private_catalog_grant(
        self,
        *,
        policy: PrivatePolicyRecord,
        storefront: PrivateStorefrontRecord,
        normalized_codes: tuple[NormalizedCustomerCode, ...],
        code_set_hash: str,
        channel: str,
        user_id: UUID | None,
        anonymous_session_id: str | None,
        issued_at: datetime,
        expires_at: datetime,
    ) -> PrivateCatalogGrantRecord:
        token_hash = hashlib.sha256(secrets.token_urlsafe(32).encode("utf-8")).hexdigest()
        model = PrivateCatalogAccessGrantModel(
            policy_id=policy.id,
            policy_version_id=policy.policy_version_id,
            growth_code_id=policy.growth_code_id,
            code_set_hash=code_set_hash,
            grant_token_hash=token_hash,
            user_id=user_id,
            anonymous_session_id=anonymous_session_id,
            auth_realm_id=storefront.auth_realm_id,
            storefront_id=storefront.id,
            sale_channel=channel,
            allowed_plan_ids=[str(item) for item in policy.target_plan_ids],
            allowed_offer_ids=[],
            status="issued",
            max_quote_conversions=policy.max_quote_conversions,
            quote_conversions_count=0,
            issued_at=issued_at,
            expires_at=expires_at,
            metadata_={
                "code_count": len(normalized_codes),
                "matched_prefixes": [code.code_prefix for code in normalized_codes],
            },
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return PrivateCatalogGrantRecord(id=model.id, expires_at=model.expires_at)
