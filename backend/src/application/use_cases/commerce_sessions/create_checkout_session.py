from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.commerce_sessions.context_resolution import ResolveQuoteContextUseCase
from src.application.use_cases.commerce_sessions.quote_serialization import (
    build_context_snapshot,
    serialize_checkout_result,
)
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutUseCase
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.presentation.dependencies.auth_realms import RealmResolution

CHECKOUT_SESSION_TTL = timedelta(minutes=30)


class QuoteSessionExpiredError(ValueError):
    pass


class QuoteSessionDriftError(ValueError):
    pass


class CheckoutSessionConflictError(ValueError):
    pass


class CreateCheckoutSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CommerceSessionRepository(session)
        self._resolver = ResolveQuoteContextUseCase(session)
        self._checkout = CheckoutUseCase(session)

    @staticmethod
    def _normalize_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def execute(
        self,
        *,
        quote_session_id: UUID,
        user_id: UUID,
        current_realm: RealmResolution,
        idempotency_key: str,
        host: str | None,
    ) -> tuple[CheckoutSessionModel, bool]:
        quote_session = await self._repo.get_quote_session_by_id(quote_session_id)
        if quote_session is None or quote_session.user_id != user_id:
            raise ValueError("Quote session not found")
        if str(quote_session.auth_realm_id) != current_realm.realm_id:
            raise ValueError("Quote session does not belong to the current auth realm")

        existing = await self._repo.get_checkout_session_by_quote_session_id(quote_session.id)
        if existing is not None:
            if existing.idempotency_key == idempotency_key:
                return existing, False
            raise CheckoutSessionConflictError("Checkout session already exists for this quote")

        now = datetime.now(UTC)
        quote_expires_at = self._normalize_utc(quote_session.expires_at)
        if quote_expires_at <= now:
            quote_session.quote_status = "expired"
            await self._session.commit()
            raise QuoteSessionExpiredError("Quote session has expired")

        current_context, current_quote_snapshot = await self._resolve_current_state(
            quote_session=quote_session,
            current_realm=current_realm,
            host=host,
            user_id=user_id,
        )

        if current_context != quote_session.context_snapshot or current_quote_snapshot != quote_session.quote_snapshot:
            quote_session.quote_status = "stale"
            await self._session.commit()
            raise QuoteSessionDriftError("Quote session is stale due to policy or pricing drift")

        checkout_session = CheckoutSessionModel(
            quote_session_id=quote_session.id,
            user_id=quote_session.user_id,
            auth_realm_id=quote_session.auth_realm_id,
            storefront_id=quote_session.storefront_id,
            merchant_profile_id=quote_session.merchant_profile_id,
            invoice_profile_id=quote_session.invoice_profile_id,
            billing_descriptor_id=quote_session.billing_descriptor_id,
            pricebook_id=quote_session.pricebook_id,
            pricebook_entry_id=quote_session.pricebook_entry_id,
            offer_id=quote_session.offer_id,
            legal_document_set_id=quote_session.legal_document_set_id,
            program_eligibility_policy_id=quote_session.program_eligibility_policy_id,
            subscription_plan_id=quote_session.subscription_plan_id,
            sale_channel=quote_session.sale_channel,
            currency_code=quote_session.currency_code,
            checkout_status="open",
            idempotency_key=idempotency_key,
            promo_code_id=quote_session.promo_code_id,
            partner_code_id=quote_session.partner_code_id,
            request_snapshot=dict(quote_session.request_snapshot),
            checkout_snapshot={
                "quote_session_id": str(quote_session.id),
                "quote_snapshot": dict(quote_session.quote_snapshot),
            },
            context_snapshot=dict(quote_session.context_snapshot),
            expires_at=min(quote_expires_at, now + CHECKOUT_SESSION_TTL),
        )
        quote_session.quote_status = "converted"
        created = await self._repo.create_checkout_session(checkout_session)
        await self._session.commit()
        await self._session.refresh(created)
        return created, True

    async def _resolve_current_state(
        self,
        *,
        quote_session: QuoteSessionModel,
        current_realm: RealmResolution,
        host: str | None,
        user_id: UUID,
    ) -> tuple[dict, dict]:
        request_snapshot = quote_session.request_snapshot
        resolved_context = await self._resolver.execute(
            current_realm=current_realm,
            storefront_key=request_snapshot.get("storefront_key"),
            host=host,
            subscription_plan_id=UUID(request_snapshot["plan_id"]),
            pricebook_key=request_snapshot.get("pricebook_key"),
            offer_key=request_snapshot.get("offer_key"),
            currency_code=request_snapshot["currency"],
            sale_channel=request_snapshot["channel"],
        )
        checkout_result = await self._checkout.execute(
            user_id=user_id,
            plan_id=UUID(request_snapshot["plan_id"]),
            promo_code=request_snapshot.get("promo_code"),
            partner_code=request_snapshot.get("partner_code"),
            use_wallet=Decimal(str(request_snapshot.get("use_wallet", 0))),
            addons=[
                CheckoutAddonInput(
                    code=addon["code"],
                    qty=addon["qty"],
                    location_code=addon.get("location_code"),
                )
                for addon in request_snapshot.get("addons", [])
            ],
            sale_channel=request_snapshot["channel"],
        )
        return build_context_snapshot(resolved_context), serialize_checkout_result(checkout_result)
