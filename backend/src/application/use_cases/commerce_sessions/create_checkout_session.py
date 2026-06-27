from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.commerce_sessions.context_resolution import ResolveQuoteContextUseCase
from src.application.use_cases.commerce_sessions.quote_serialization import (
    build_context_snapshot,
    build_subscription_snapshot,
    restore_protected_request_code,
    restore_protected_request_codes,
    serialize_checkout_result,
)
from src.application.use_cases.growth_code_sets.ledger import reservation_ids_from_snapshot
from src.application.use_cases.growth_code_sets.snapshots import (
    attach_growth_checkout_integrity,
    canonical_growth_checkout_snapshot,
)
from src.application.use_cases.growth_codes.reservations import GrowthCodeReservationService
from src.application.use_cases.partner_attribution.attribution import (
    EnsurePendingPartnerAttributionClaimedCommand,
    EnsurePendingPartnerAttributionClaimedResult,
    EnsurePendingPartnerAttributionClaimedUseCase,
    PartnerAttributionError,
)
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutCodeBasketInput, CheckoutUseCase
from src.config.settings import settings
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.growth_code_set_model import CheckoutCodeSetModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.private_catalog_repo import SqlAlchemyPrivateCatalogRepository
from src.infrastructure.monitoring.metrics import (
    commerce_checkout_session_duration_seconds,
    commerce_checkout_sessions_total,
    commerce_quote_invalidations_total,
)
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
        self._growth_codes = GrowthCodeRepository(session)
        self._reservations = GrowthCodeReservationService(session)
        self._partner_attribution = EnsurePendingPartnerAttributionClaimedUseCase(session)
        self._private_catalog = SqlAlchemyPrivateCatalogRepository(session)

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
        partner_attribution_cookie_token: str | None = None,
        source_host: str | None = None,
        source_path: str | None = None,
        campaign_params: dict[str, str] | None = None,
    ) -> tuple[CheckoutSessionModel, bool]:
        started_at = perf_counter()
        metric_channel = "unknown"
        metric_currency = "unknown"
        try:
            quote_session = await self._repo.get_quote_session_by_id(quote_session_id)
            if quote_session is None or quote_session.user_id != user_id:
                raise ValueError("Quote session not found")
            metric_channel = quote_session.sale_channel
            metric_currency = quote_session.currency_code
            if str(quote_session.auth_realm_id) != current_realm.realm_id:
                raise ValueError("Quote session does not belong to the current auth realm")

            existing = await self._repo.get_checkout_session_by_quote_session_id(quote_session.id)
            if existing is not None:
                if existing.idempotency_key == idempotency_key:
                    _record_checkout_metric(
                        channel=metric_channel,
                        currency=metric_currency,
                        status="idempotent_replay",
                        started_at=started_at,
                    )
                    return existing, False
                raise CheckoutSessionConflictError("Checkout session already exists for this quote")

            now = datetime.now(UTC)
            quote_expires_at = self._normalize_utc(quote_session.expires_at)
            if quote_expires_at <= now:
                quote_session.quote_status = "expired"
                await self._reservations.release_for_quote(
                    quote_session_id=quote_session.id,
                    reason="quote_session_expired",
                    status="expired",
                )
                await self._session.commit()
                raise QuoteSessionExpiredError("Quote session has expired")

            partner_attribution = await self._ensure_partner_attribution_claimed(
                user_id=user_id,
                current_realm=current_realm,
                cookie_token=partner_attribution_cookie_token,
                quote_session_id=quote_session.id,
                source_host=source_host,
                source_path=source_path,
                campaign_params=campaign_params,
                sale_channel=quote_session.sale_channel,
            )
            partner_attribution_snapshot = _build_partner_attribution_snapshot(partner_attribution)
            if partner_attribution_snapshot is not None:
                quote_session.quote_snapshot = attach_growth_checkout_integrity(
                    {
                        **dict(quote_session.quote_snapshot or {}),
                        "partner_attribution": partner_attribution_snapshot,
                    },
                    producer="cybervpn-backend.checkout_session",
                )
                await self._session.flush()

            current_context, current_quote_snapshot = await self._resolve_current_state(
                quote_session=quote_session,
                current_realm=current_realm,
                host=host,
                user_id=user_id,
            )

            quote_drifted = _sanitize_quote_snapshot(current_quote_snapshot) != _sanitize_quote_snapshot(
                quote_session.quote_snapshot
            )
            if current_context != quote_session.context_snapshot or quote_drifted:
                quote_session.quote_status = "stale"
                await self._reservations.release_for_quote(
                    quote_session_id=quote_session.id,
                    reason="quote_session_stale",
                )
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
                code_set_id=quote_session.code_set_id,
                private_catalog_access_grant_id=quote_session.private_catalog_access_grant_id,
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
            if quote_session.private_catalog_access_grant_id is not None:
                await self._private_catalog.attach_grant_to_checkout(
                    grant_id=quote_session.private_catalog_access_grant_id,
                    checkout_session_id=created.id,
                )
            await self._bind_reservation_to_checkout_session(quote_session=quote_session, checkout_session=created)
            await self._session.commit()
            await self._session.refresh(created)
        except QuoteSessionExpiredError:
            commerce_quote_invalidations_total.labels(reason="expired").inc()
            _record_checkout_metric(
                channel=metric_channel,
                currency=metric_currency,
                status="expired",
                started_at=started_at,
            )
            raise
        except QuoteSessionDriftError:
            commerce_quote_invalidations_total.labels(reason="stale").inc()
            _record_checkout_metric(
                channel=metric_channel,
                currency=metric_currency,
                status="stale",
                started_at=started_at,
            )
            raise
        except CheckoutSessionConflictError:
            commerce_quote_invalidations_total.labels(reason="conflict").inc()
            _record_checkout_metric(
                channel=metric_channel,
                currency=metric_currency,
                status="conflict",
                started_at=started_at,
            )
            raise
        except Exception:
            _record_checkout_metric(
                channel=metric_channel,
                currency=metric_currency,
                status="failure",
                started_at=started_at,
            )
            raise

        _record_checkout_metric(
            channel=metric_channel,
            currency=metric_currency,
            status="created",
            started_at=started_at,
        )
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
            currency=request_snapshot["currency"],
            catalog_base_price=Decimal(str(resolved_context.pricebook_entry.visible_price)),
            code_input=restore_protected_request_code(request_snapshot, "code_input"),
            promo_code=restore_protected_request_code(request_snapshot, "promo_code"),
            partner_code=restore_protected_request_code(request_snapshot, "partner_code"),
            use_wallet=Decimal(str(request_snapshot.get("use_wallet", 0))),
            storefront_id=quote_session.storefront_id,
            private_catalog_grant_id=_optional_uuid(request_snapshot.get("private_catalog_grant_id")),
            private_catalog_quote_session_id=quote_session.id,
            addons=[
                CheckoutAddonInput(
                    code=addon["code"],
                    qty=addon["qty"],
                    location_code=addon.get("location_code"),
                )
                for addon in request_snapshot.get("addons", [])
            ],
            code_basket=[
                CheckoutCodeBasketInput(
                    code=str(item["code"]),
                    client_slot_id=item.get("client_slot_id"),
                )
                for item in restore_protected_request_codes(request_snapshot)
            ],
            sale_channel=request_snapshot["channel"],
        )
        current_quote_snapshot = serialize_checkout_result(
            checkout_result,
            subscription_snapshot=build_subscription_snapshot(
                result=checkout_result,
                context=resolved_context,
            ),
        )
        if quote_session.code_set_id is not None and checkout_result.code_set_applications:
            stored_code_set = dict((quote_session.quote_snapshot or {}).get("code_set") or {})
            stored_applications = list(stored_code_set.get("applications") or [])
            if stored_applications:
                stored_code_set["applications"] = stored_applications
                current_quote_snapshot["code_set_id"] = str(quote_session.code_set_id)
                current_quote_snapshot["code_set_hash"] = (quote_session.quote_snapshot or {}).get("code_set_hash")
                current_quote_snapshot["reservation_group_id"] = (quote_session.quote_snapshot or {}).get(
                    "reservation_group_id"
                )
                current_quote_snapshot["code_set"] = stored_code_set
                code_resolution = dict(current_quote_snapshot.get("code_resolution") or {})
                if code_resolution:
                    code_resolution["reservation_group_id"] = current_quote_snapshot.get("reservation_group_id")
                    current_quote_snapshot["code_resolution"] = code_resolution
                current_quote_snapshot = attach_growth_checkout_integrity(
                    current_quote_snapshot,
                    producer="cybervpn-backend.checkout_session.reprice_code_set",
                )
        return build_context_snapshot(resolved_context), current_quote_snapshot

    async def _bind_reservation_to_checkout_session(
        self,
        *,
        quote_session: QuoteSessionModel,
        checkout_session: CheckoutSessionModel,
    ) -> None:
        reservation_id = _extract_reservation_id(quote_session.quote_snapshot)
        reservation_ids = reservation_ids_from_snapshot(quote_session.quote_snapshot)
        if reservation_id is not None and reservation_id not in reservation_ids:
            reservation_ids.append(reservation_id)
        if not reservation_ids:
            return
        for reservation_id in sorted(reservation_ids, key=str):
            reservation = await self._growth_codes.get_reservation_by_id(reservation_id)
            if reservation is None:
                continue
            reservation.checkout_session_id = checkout_session.id
        if quote_session.code_set_id is not None:
            code_set = await self._session.get(CheckoutCodeSetModel, quote_session.code_set_id)
            if code_set is not None:
                code_set.checkout_session_id = checkout_session.id
                code_set.status = "checkout_open"
            checkout_session.code_set_id = quote_session.code_set_id
        await self._reservations.bind_groups_to_checkout_session(
            quote_session_id=quote_session.id,
            checkout_session_id=checkout_session.id,
        )
        await self._session.flush()

    async def _ensure_partner_attribution_claimed(
        self,
        *,
        user_id: UUID,
        current_realm: RealmResolution,
        cookie_token: str | None,
        quote_session_id: UUID,
        source_host: str | None = None,
        source_path: str | None = None,
        campaign_params: dict[str, str] | None = None,
        sale_channel: str | None = None,
    ) -> EnsurePendingPartnerAttributionClaimedResult | None:
        if not settings.partner_attribution_enabled or not cookie_token:
            return None
        try:
            return await self._partner_attribution.execute(
                EnsurePendingPartnerAttributionClaimedCommand(
                    user_id=user_id,
                    cookie_token=cookie_token,
                    current_realm=current_realm,
                    quote_session_id=quote_session_id,
                    source_host=source_host,
                    source_path=source_path,
                    campaign_params=campaign_params,
                    sale_channel=sale_channel,
                )
            )
        except PartnerAttributionError:
            raise
        except Exception as exc:
            raise PartnerAttributionError(
                code="PARTNER_ATTRIBUTION_TRANSIENT_FAILURE",
                message="Partner attribution is temporarily unavailable.",
                status_code=503,
            ) from exc


def _extract_reservation_id(quote_snapshot: dict | None) -> UUID | None:
    code_resolution = (quote_snapshot or {}).get("code_resolution") or {}
    raw_value = code_resolution.get("reservation_id")
    if not raw_value:
        return None
    return UUID(str(raw_value))


def _optional_uuid(raw_value: object) -> UUID | None:
    if raw_value is None or raw_value == "":
        return None
    return UUID(str(raw_value))


def _sanitize_quote_snapshot(snapshot: dict | None) -> dict:
    sanitized = canonical_growth_checkout_snapshot(snapshot)
    sanitized.pop("partner_attribution", None)
    sanitized.pop("partner_commission_contract_snapshot", None)
    sanitized.pop("code_set", None)
    sanitized.pop("code_set_id", None)
    sanitized.pop("code_set_hash", None)
    sanitized.pop("reservation_group_id", None)
    code_resolution = dict(sanitized.get("code_resolution") or {})
    if code_resolution:
        code_resolution["reservation_id"] = None
        code_resolution.pop("reservation_group_id", None)
        policy_snapshot = dict(code_resolution.get("policy_snapshot") or {})
        if policy_snapshot:
            policy_snapshot.pop("commission_contract_snapshot", None)
            code_resolution["policy_snapshot"] = policy_snapshot
        sanitized["code_resolution"] = code_resolution
    return sanitized


def _build_partner_attribution_snapshot(
    result: EnsurePendingPartnerAttributionClaimedResult | None,
) -> dict[str, str | None] | None:
    if result is None:
        return None
    return {
        "source": "server_side_checkout_safety_net",
        "status": result.status,
        "attribution_session_id": str(result.attribution_session_id) if result.attribution_session_id else None,
        "partner_account_id": str(result.partner_account_id) if result.partner_account_id else None,
        "partner_code_id": str(result.partner_code_id) if result.partner_code_id else None,
        "binding_id": str(result.binding_id) if result.binding_id else None,
        "claim_touchpoint_id": str(result.claim_touchpoint_id) if result.claim_touchpoint_id else None,
        "quote_touchpoint_id": str(result.quote_touchpoint_id) if result.quote_touchpoint_id else None,
    }


def _record_checkout_metric(
    *,
    channel: str,
    currency: str,
    status: str,
    started_at: float,
) -> None:
    commerce_checkout_sessions_total.labels(
        channel=channel,
        currency=currency,
        status=status,
    ).inc()
    commerce_checkout_session_duration_seconds.labels(
        channel=channel,
        status=status,
    ).observe(perf_counter() - started_at)
