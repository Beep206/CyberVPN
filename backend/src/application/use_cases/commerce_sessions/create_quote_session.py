from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.attribution import RecordAttributionTouchpointUseCase
from src.application.use_cases.commerce_sessions.context_resolution import ResolveQuoteContextUseCase
from src.application.use_cases.commerce_sessions.quote_serialization import (
    build_context_snapshot,
    build_request_snapshot,
    serialize_checkout_result,
)
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutUseCase
from src.domain.enums import AttributionTouchpointType
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.presentation.dependencies.auth_realms import RealmResolution

QUOTE_SESSION_TTL = timedelta(minutes=30)


class CreateQuoteSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CommerceSessionRepository(session)
        self._checkout = CheckoutUseCase(session)
        self._resolver = ResolveQuoteContextUseCase(session)
        self._touchpoints = RecordAttributionTouchpointUseCase(session)

    async def execute(
        self,
        *,
        user_id: UUID,
        current_realm: RealmResolution,
        storefront_key: str | None,
        host: str | None,
        plan_id: UUID,
        pricebook_key: str | None,
        offer_key: str | None,
        promo_code: str | None,
        partner_code: str | None,
        use_wallet: float,
        currency: str,
        channel: str,
        addons: list[dict],
        source_host: str | None = None,
        source_path: str | None = None,
        campaign_params: dict[str, str] | None = None,
    ) -> QuoteSessionModel:
        resolved_context = await self._resolver.execute(
            current_realm=current_realm,
            storefront_key=storefront_key,
            host=host,
            subscription_plan_id=plan_id,
            pricebook_key=pricebook_key,
            offer_key=offer_key,
            currency_code=currency,
            sale_channel=channel,
        )

        checkout_result = await self._checkout.execute(
            user_id=user_id,
            plan_id=plan_id,
            promo_code=promo_code,
            partner_code=partner_code,
            use_wallet=Decimal(str(use_wallet)),
            addons=[
                CheckoutAddonInput(
                    code=addon["code"],
                    qty=addon["qty"],
                    location_code=addon.get("location_code"),
                )
                for addon in addons
            ],
            sale_channel=channel,
        )

        now = datetime.now(UTC)
        model = QuoteSessionModel(
            user_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            storefront_id=resolved_context.storefront.id,
            merchant_profile_id=resolved_context.merchant_profile.id,
            invoice_profile_id=resolved_context.invoice_profile.id,
            billing_descriptor_id=resolved_context.billing_descriptor.id,
            pricebook_id=resolved_context.pricebook.id,
            pricebook_entry_id=resolved_context.pricebook_entry.id,
            offer_id=resolved_context.offer.id,
            legal_document_set_id=resolved_context.legal_document_set.id,
            program_eligibility_policy_id=(
                resolved_context.program_eligibility_policy.id
                if resolved_context.program_eligibility_policy
                else None
            ),
            subscription_plan_id=plan_id,
            sale_channel=channel,
            currency_code=currency.upper(),
            quote_status="open",
            promo_code=promo_code.strip() if promo_code else None,
            promo_code_id=checkout_result.promo_code_id,
            partner_code_id=checkout_result.partner_code_id,
            request_snapshot=build_request_snapshot(
                storefront_key=resolved_context.storefront.storefront_key,
                pricebook_key=resolved_context.pricebook.pricebook_key,
                offer_key=resolved_context.offer.offer_key,
                plan_id=str(plan_id),
                currency=currency.upper(),
                channel=channel,
                promo_code=promo_code.strip() if promo_code else None,
                partner_code=partner_code.strip() if partner_code else None,
                use_wallet=use_wallet,
                addons=addons,
            ),
            quote_snapshot=serialize_checkout_result(checkout_result),
            context_snapshot=build_context_snapshot(resolved_context),
            expires_at=now + QUOTE_SESSION_TTL,
        )
        created = await self._repo.create_quote_session(model)

        await self._touchpoints.execute(
            current_realm=current_realm,
            touchpoint_type=AttributionTouchpointType.STOREFRONT_ORIGIN.value,
            user_id=user_id,
            storefront_id=resolved_context.storefront.id,
            quote_session_id=created.id,
            sale_channel=channel,
            source_host=source_host,
            source_path=source_path,
            campaign_params=dict(campaign_params or {}),
            evidence_payload={
                "source": "quote_session_create",
                "storefront_key": resolved_context.storefront.storefront_key,
            },
            commit=False,
        )
        normalized_partner_code = partner_code.strip() if partner_code else None
        if normalized_partner_code and checkout_result.partner_code_id is not None:
            await self._touchpoints.execute(
                current_realm=current_realm,
                touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
                user_id=user_id,
                storefront_id=resolved_context.storefront.id,
                quote_session_id=created.id,
                partner_code=normalized_partner_code,
                partner_code_id=checkout_result.partner_code_id,
                sale_channel=channel,
                source_host=source_host,
                source_path=source_path,
                campaign_params=dict(campaign_params or {}),
                evidence_payload={
                    "source": "quote_session_create",
                    "entry_mode": "request_payload",
                    "storefront_key": resolved_context.storefront.storefront_key,
                },
                commit=False,
            )

        await self._session.commit()
        await self._session.refresh(created)
        return created
