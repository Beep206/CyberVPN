from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.attribution import RecordAttributionTouchpointUseCase
from src.application.use_cases.commerce_sessions.context_resolution import ResolveQuoteContextUseCase
from src.application.use_cases.commerce_sessions.quote_serialization import (
    build_context_snapshot,
    build_request_snapshot,
    build_subscription_snapshot,
    serialize_checkout_result,
)
from src.application.use_cases.growth_code_sets.fx import minor_units_for_currency
from src.application.use_cases.growth_code_sets.ledger import (
    attach_code_set_to_quote_snapshot,
    build_legacy_quote_application,
    code_set_hash_for_applications,
)
from src.application.use_cases.growth_codes.reservations import (
    GrowthCodeReservationService,
    ReservationCapacityContext,
)
from src.application.use_cases.growth_risk.runtime_guard import evaluate_growth_runtime_risk
from src.application.use_cases.partner_attribution.attribution import (
    EnsurePendingPartnerAttributionClaimedCommand,
    EnsurePendingPartnerAttributionClaimedResult,
    EnsurePendingPartnerAttributionClaimedUseCase,
    PartnerAttributionError,
)
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutCodeBasketInput, CheckoutUseCase
from src.config.settings import settings
from src.domain.enums import AttributionTouchpointType, GrowthCodeType
from src.infrastructure.database.models.growth_code_set_model import CheckoutCodeApplicationModel, CheckoutCodeSetModel
from src.infrastructure.database.models.growth_risk_fx_model import FxDiscountConversionModel, FxRateSnapshotModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.infrastructure.database.repositories.private_catalog_repo import SqlAlchemyPrivateCatalogRepository
from src.infrastructure.monitoring.metrics import (
    commerce_checkout_addons_total,
    commerce_quote_session_duration_seconds,
    commerce_quote_sessions_total,
)
from src.presentation.dependencies.auth_realms import RealmResolution

QUOTE_SESSION_TTL = timedelta(minutes=30)


class CreateQuoteSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CommerceSessionRepository(session)
        self._checkout = CheckoutUseCase(session)
        self._resolver = ResolveQuoteContextUseCase(session)
        self._touchpoints = RecordAttributionTouchpointUseCase(session)
        self._partner_attribution = EnsurePendingPartnerAttributionClaimedUseCase(session)
        self._reservations = GrowthCodeReservationService(session)
        self._private_catalog = SqlAlchemyPrivateCatalogRepository(session)

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
        code_input: str | None,
        promo_code: str | None,
        partner_code: str | None,
        use_wallet: float,
        currency: str,
        channel: str,
        addons: list[dict],
        private_catalog_grant_id: UUID | None = None,
        source_host: str | None = None,
        source_path: str | None = None,
        campaign_params: dict[str, str] | None = None,
        partner_attribution_cookie_token: str | None = None,
        private_catalog_anonymous_session_id: str | None = None,
        codes: list[dict] | None = None,
    ) -> QuoteSessionModel:
        started_at = perf_counter()
        normalized_currency = currency.upper()
        try:
            pending_attribution = await self._ensure_partner_attribution_claimed(
                user_id=user_id,
                current_realm=current_realm,
                cookie_token=partner_attribution_cookie_token,
                source_host=source_host,
                source_path=source_path,
                campaign_params=campaign_params,
                sale_channel=channel,
            )
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
                currency=normalized_currency,
                catalog_base_price=Decimal(str(resolved_context.pricebook_entry.visible_price)),
                code_input=code_input,
                promo_code=promo_code,
                partner_code=partner_code,
                code_basket=[
                    CheckoutCodeBasketInput(
                        code=str(item["code"]),
                        client_slot_id=item.get("client_slot_id"),
                    )
                    for item in codes or []
                ],
                use_wallet=Decimal(str(use_wallet)),
                storefront_id=resolved_context.storefront.id,
                private_catalog_grant_id=private_catalog_grant_id,
                private_catalog_anonymous_session_id=private_catalog_anonymous_session_id,
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
            subscription_snapshot = build_subscription_snapshot(
                result=checkout_result,
                context=resolved_context,
            )
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
                currency_code=normalized_currency,
                quote_status="open",
                promo_code=promo_code.strip() if promo_code else None,
                promo_code_id=checkout_result.promo_code_id,
                partner_code_id=checkout_result.partner_code_id,
                private_catalog_access_grant_id=checkout_result.private_catalog_grant_id,
                request_snapshot=build_request_snapshot(
                    storefront_key=resolved_context.storefront.storefront_key,
                    pricebook_key=resolved_context.pricebook.pricebook_key,
                    offer_key=resolved_context.offer.offer_key,
                    plan_id=str(plan_id),
                    currency=normalized_currency,
                    channel=channel,
                    code_input=checkout_result.code_input,
                    promo_code=promo_code.strip() if promo_code else None,
                    partner_code=partner_code.strip() if partner_code else None,
                    codes=codes or [],
                    use_wallet=use_wallet,
                    addons=addons,
                    private_catalog_grant_id=(
                        str(checkout_result.private_catalog_grant_id)
                        if checkout_result.private_catalog_grant_id is not None
                        else None
                    ),
                ),
                quote_snapshot=serialize_checkout_result(
                    checkout_result,
                    subscription_snapshot=subscription_snapshot,
                ),
                context_snapshot=build_context_snapshot(resolved_context),
                expires_at=now + QUOTE_SESSION_TTL,
            )
            created = await self._repo.create_quote_session(model)
            if created.private_catalog_access_grant_id is not None:
                await self._private_catalog.attach_grant_to_quote(
                    grant_id=created.private_catalog_access_grant_id,
                    quote_session_id=created.id,
                )
            linked_attribution = await self._ensure_partner_attribution_claimed(
                user_id=user_id,
                current_realm=current_realm,
                cookie_token=partner_attribution_cookie_token,
                quote_session_id=created.id,
                source_host=source_host,
                source_path=source_path,
                campaign_params=campaign_params,
                sale_channel=channel,
            )
            if checkout_result.code_set_applications:
                await self._persist_code_set_for_quote(
                    created=created,
                    checkout_result=checkout_result,
                    subscription_snapshot=subscription_snapshot,
                    applications=[dict(item) for item in checkout_result.code_set_applications],
                    user_id=user_id,
                    acceptance_mode=checkout_result.code_set_acceptance_mode or "all_or_nothing",
                    producer="cybervpn-backend.quote_code_set.basket",
                )
            elif _should_reserve_growth_code(checkout_result):
                code_resolution = checkout_result.code_resolution
                if code_resolution is None or code_resolution.growth_code_id is None:
                    raise ValueError("Accepted growth code has no canonical identifier")
                reservation = await self._reservations.reserve_for_quote(
                    growth_code_id=code_resolution.growth_code_id,
                    quote_session_id=created.id,
                    user_id=user_id,
                    expires_at=created.expires_at,
                )
                checkout_result.reservation_id = reservation.id
                reserved_quote_snapshot = serialize_checkout_result(
                    checkout_result,
                    subscription_snapshot=subscription_snapshot,
                )
                application = build_legacy_quote_application(reserved_quote_snapshot)
                if application is None:
                    raise ValueError("CODE_SET_APPLICATION_MISSING")
                code_set_hash = code_set_hash_for_applications([application])
                code_set = CheckoutCodeSetModel(
                    code_set_hash=code_set_hash,
                    user_id=user_id,
                    anonymous_session_id=None,
                    auth_realm_id=created.auth_realm_id,
                    storefront_id=created.storefront_id,
                    sale_channel=created.sale_channel,
                    action_context="checkout",
                    status="reserved",
                    acceptance_mode="single_legacy_code",
                    aggregate_result={
                        "snapshot_version": "checkout_code_set.single_legacy.v1",
                        "accepted": True,
                        "currency_code": created.currency_code,
                        "application_count": 1,
                        "code_ref": application.get("code_ref"),
                    },
                    risk_snapshot={
                        "risk_decision_ids": [
                            application["risk_decision_id"],
                        ]
                        if application.get("risk_decision_id")
                        else [],
                    },
                    private_access_grant_id=created.private_catalog_access_grant_id,
                    quote_session_id=created.id,
                )
                self._session.add(code_set)
                await self._session.flush()
                group = await self._reservations.create_group_for_quote(
                    code_set_id=code_set.id,
                    reservations=[reservation],
                    user_id=user_id,
                    quote_session_id=created.id,
                    expires_at=created.expires_at,
                    idempotency_key=f"quote:{created.id}:code-set:{code_set_hash}",
                )
                application["reservation_group_id"] = str(group.id)
                code_set.aggregate_result = {
                    **dict(code_set.aggregate_result or {}),
                    "reservation_group_id": str(group.id),
                    "reservation_ids": [str(reservation.id)],
                }
                application_model = CheckoutCodeApplicationModel(
                    code_set_id=code_set.id,
                    position_entered=int(application.get("position_entered") or 0),
                    canonical_order=int(application.get("canonical_order") or 0),
                    growth_code_id=code_resolution.growth_code_id,
                    legacy_code_type=str(application.get("legacy_code_type") or "promo"),
                    legacy_code_id=code_resolution.promo_code_id,
                    masked_code=str(application.get("masked_code") or ""),
                    roles={
                        "values": list(application.get("roles") or []),
                        "source": "single_legacy_field",
                    },
                    resolution_status=str(application.get("status") or "accepted"),
                    reject_reason=None,
                    conflict_code=code_resolution.conflict_code,
                    policy_version_id=_optional_uuid(application.get("policy_version_id")),
                    risk_decision_id=_optional_uuid(application.get("risk_decision_id")),
                    fx_conversion_id=_application_fx_conversion_id(application),
                    reservation_id=reservation.id,
                    discount_snapshot=dict(application.get("discount") or {}),
                    benefits_snapshot={"items": list(application.get("benefits") or [])},
                    private_access_snapshot=dict(application.get("private_access") or {}),
                    evaluation_trace=dict(application.get("evaluation_trace") or {}),
                )
                self._session.add(application_model)
                await self._session.flush()
                await _persist_fx_conversion_for_application(self._session, application_model, application)
                created.code_set_id = code_set.id
                created.quote_snapshot = attach_code_set_to_quote_snapshot(
                    reserved_quote_snapshot,
                    code_set_id=code_set.id,
                    code_set_hash=code_set_hash,
                    applications=[application],
                    reservation_group_id=group.id,
                    acceptance_mode="single_legacy_code",
                    producer="cybervpn-backend.quote_code_set",
                )
                await self._session.flush()

            attribution_snapshot = _build_partner_attribution_snapshot(linked_attribution or pending_attribution)
            if attribution_snapshot is not None:
                created.quote_snapshot = {
                    **dict(created.quote_snapshot or {}),
                    "partner_attribution": attribution_snapshot,
                }
                await self._session.flush()

            normalized_partner_code = partner_code.strip() if partner_code else None
            if settings.partner_attribution_enabled:
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
                explicit_partner_code = _explicit_partner_code_for_touchpoint(
                    normalized_partner_code=normalized_partner_code,
                    checkout_result=checkout_result,
                )
                if explicit_partner_code and checkout_result.partner_code_id is not None:
                    await self._touchpoints.execute(
                        current_realm=current_realm,
                        touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
                        user_id=user_id,
                        storefront_id=resolved_context.storefront.id,
                        quote_session_id=created.id,
                        partner_code=explicit_partner_code,
                        partner_code_id=checkout_result.partner_code_id,
                        sale_channel=channel,
                        source_host=source_host,
                        source_path=source_path,
                        campaign_params=dict(campaign_params or {}),
                        evidence_payload={
                            "source": "quote_session_create",
                            "entry_mode": ("request_payload" if normalized_partner_code else "unified_code_input"),
                            "storefront_key": resolved_context.storefront.storefront_key,
                            "policy_snapshot": _build_partner_commission_policy_snapshot(checkout_result),
                        },
                        commit=False,
                    )

            await self._session.commit()
            await self._session.refresh(created)
        except Exception:
            commerce_quote_sessions_total.labels(
                channel=channel,
                currency=normalized_currency,
                status="failure",
            ).inc()
            commerce_quote_session_duration_seconds.labels(
                channel=channel,
                status="failure",
            ).observe(perf_counter() - started_at)
            if addons:
                commerce_checkout_addons_total.labels(channel=channel, status="quote_failure").inc(len(addons))
            raise

        commerce_quote_sessions_total.labels(
            channel=channel,
            currency=normalized_currency,
            status="created",
        ).inc()
        commerce_quote_session_duration_seconds.labels(
            channel=channel,
            status="created",
        ).observe(perf_counter() - started_at)
        if addons:
            commerce_checkout_addons_total.labels(channel=channel, status="quoted").inc(len(addons))
        return created

    async def _persist_code_set_for_quote(
        self,
        *,
        created: QuoteSessionModel,
        checkout_result,
        subscription_snapshot: dict,
        applications: list[dict],
        user_id: UUID,
        acceptance_mode: str,
        producer: str,
    ) -> None:
        if not applications:
            return
        reservable_code_ids: list[UUID] = []
        capacity_contexts: dict[UUID, ReservationCapacityContext] = {}
        for application in applications:
            if str(application.get("status") or "") != "accepted":
                continue
            growth_code_id = _optional_uuid(application.get("growth_code_id"))
            if growth_code_id is None:
                continue
            reservable_code_ids.append(growth_code_id)
            capacity_contexts[growth_code_id] = _capacity_context_from_application(application)

        if not reservable_code_ids:
            raise ValueError("CODE_SET_RESERVATION_MISSING")

        is_zero_gateway_quote = Decimal(str(checkout_result.gateway_amount)) <= Decimal("0")
        risk_result = await evaluate_growth_runtime_risk(
            session=self._session,
            action_context="reservation",
            user_id=user_id,
            auth_realm_id=created.auth_realm_id,
            storefront_id=created.storefront_id,
            high_risk_context=is_zero_gateway_quote or created.private_catalog_access_grant_id is not None,
            features={
                "checkpoint": "reservation",
                "channel": created.sale_channel,
                "currency": created.currency_code,
                "private_catalog": created.private_catalog_access_grant_id is not None,
                "zero_gateway": is_zero_gateway_quote,
                "stacking_count": len(applications),
                "discount_amount": str(checkout_result.discount_amount),
                "gateway_amount": str(checkout_result.gateway_amount),
            },
            private_grant_id=created.private_catalog_access_grant_id,
            quote_session_id=created.id,
            enforce=True,
        )
        if risk_result.decision.decision_id is not None:
            for application in applications:
                application.setdefault("risk_decision_id", str(risk_result.decision.decision_id))
                application.setdefault("risk_subject_id", str(risk_result.decision.risk_subject_id))

        reservations_by_code_id = await self._reservations.reserve_many_for_quote(
            growth_code_ids=reservable_code_ids,
            quote_session_id=created.id,
            user_id=user_id,
            expires_at=created.expires_at,
            capacity_contexts=capacity_contexts,
        )
        reservations = [
            reservations_by_code_id[growth_code_id] for growth_code_id in sorted(reservations_by_code_id, key=str)
        ]
        for application in applications:
            growth_code_id = _optional_uuid(application.get("growth_code_id"))
            if growth_code_id is not None and growth_code_id in reservations_by_code_id:
                application["reservation_id"] = str(reservations_by_code_id[growth_code_id].id)

        code_set_hash = code_set_hash_for_applications(applications)
        code_set = CheckoutCodeSetModel(
            code_set_hash=code_set_hash,
            user_id=user_id,
            anonymous_session_id=None,
            auth_realm_id=created.auth_realm_id,
            storefront_id=created.storefront_id,
            sale_channel=created.sale_channel,
            action_context="checkout",
            status="reserved",
            acceptance_mode=acceptance_mode,
            aggregate_result={
                "snapshot_version": "checkout_code_set.v6",
                "accepted": True,
                "currency_code": created.currency_code,
                "application_count": len(applications),
                "accepted_count": len([item for item in applications if str(item.get("status") or "") == "accepted"]),
                "discount_amount": str(checkout_result.discount_amount),
                "wallet_amount": str(checkout_result.wallet_amount),
                "gateway_amount": str(checkout_result.gateway_amount),
            },
            risk_snapshot={
                "risk_decision_ids": [
                    str(application["risk_decision_id"])
                    for application in applications
                    if application.get("risk_decision_id")
                ],
            },
            private_access_grant_id=created.private_catalog_access_grant_id,
            quote_session_id=created.id,
        )
        self._session.add(code_set)
        await self._session.flush()

        group = await self._reservations.create_group_for_quote(
            code_set_id=code_set.id,
            reservations=reservations,
            user_id=user_id,
            quote_session_id=created.id,
            expires_at=created.expires_at,
            idempotency_key=f"quote:{created.id}:code-set:{code_set_hash}",
        )
        for application in applications:
            application["reservation_group_id"] = str(group.id)
        code_set.aggregate_result = {
            **dict(code_set.aggregate_result or {}),
            "reservation_group_id": str(group.id),
            "reservation_ids": [str(reservation.id) for reservation in reservations],
        }
        for application in applications:
            application_model = CheckoutCodeApplicationModel(
                code_set_id=code_set.id,
                position_entered=int(application.get("position_entered") or 0),
                canonical_order=int(application.get("canonical_order") or 0),
                growth_code_id=_optional_uuid(application.get("growth_code_id")),
                legacy_code_type=str(application.get("legacy_code_type") or "growth_code"),
                legacy_code_id=_optional_uuid(application.get("legacy_code_id")),
                masked_code=str(application.get("masked_code") or ""),
                roles={
                    "values": list(application.get("roles") or []),
                    "source": "code_basket",
                },
                resolution_status=str(application.get("status") or "accepted"),
                reject_reason=application.get("reject_reason"),
                conflict_code=application.get("conflict_code"),
                policy_version_id=_optional_uuid(application.get("policy_version_id")),
                risk_decision_id=_optional_uuid(application.get("risk_decision_id")),
                fx_conversion_id=_application_fx_conversion_id(application),
                reservation_id=_optional_uuid(application.get("reservation_id")),
                discount_snapshot=dict(application.get("discount") or {}),
                benefits_snapshot={"items": list(application.get("benefits") or [])},
                private_access_snapshot=dict(application.get("private_access") or {}),
                evaluation_trace=dict(application.get("evaluation_trace") or {}),
            )
            self._session.add(application_model)
            await self._session.flush()
            await _persist_fx_conversion_for_application(self._session, application_model, application)

        reserved_quote_snapshot = serialize_checkout_result(
            checkout_result,
            subscription_snapshot=subscription_snapshot,
        )
        created.code_set_id = code_set.id
        created.quote_snapshot = attach_code_set_to_quote_snapshot(
            reserved_quote_snapshot,
            code_set_id=code_set.id,
            code_set_hash=code_set_hash,
            applications=applications,
            reservation_group_id=group.id,
            acceptance_mode=acceptance_mode,
            producer=producer,
        )
        await self._session.flush()

    async def _ensure_partner_attribution_claimed(
        self,
        *,
        user_id: UUID,
        current_realm: RealmResolution,
        cookie_token: str | None,
        quote_session_id: UUID | None = None,
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


def _should_reserve_growth_code(checkout_result) -> bool:
    if checkout_result.code_resolution is None:
        return False
    if not checkout_result.code_resolution.accepted:
        return False
    if checkout_result.code_resolution.growth_code_id is None:
        return False
    return checkout_result.code_resolution.code_type == GrowthCodeType.PROMO


def _build_partner_attribution_snapshot(
    result: EnsurePendingPartnerAttributionClaimedResult | None,
) -> dict[str, str | None] | None:
    if result is None:
        return None
    return {
        "source": "server_side_quote_safety_net",
        "status": result.status,
        "attribution_session_id": str(result.attribution_session_id) if result.attribution_session_id else None,
        "partner_account_id": str(result.partner_account_id) if result.partner_account_id else None,
        "partner_code_id": str(result.partner_code_id) if result.partner_code_id else None,
        "binding_id": str(result.binding_id) if result.binding_id else None,
        "claim_touchpoint_id": str(result.claim_touchpoint_id) if result.claim_touchpoint_id else None,
        "quote_touchpoint_id": str(result.quote_touchpoint_id) if result.quote_touchpoint_id else None,
    }


def _explicit_partner_code_for_touchpoint(*, normalized_partner_code: str | None, checkout_result) -> str | None:
    if normalized_partner_code:
        return normalized_partner_code
    if (
        checkout_result.code_resolution is not None
        and checkout_result.code_resolution.code_type == GrowthCodeType.PARTNER
        and checkout_result.partner_code_id is not None
    ):
        return checkout_result.code_input
    return None


def _build_partner_commission_policy_snapshot(checkout_result) -> dict:
    snapshot = dict(checkout_result.partner_commission_contract_snapshot or {})
    policy_snapshot = {
        "partner_account_id": snapshot.get("partner_account_id"),
        "partner_user_id": snapshot.get("partner_user_id"),
        "partner_code_id": snapshot.get("partner_code_id")
        or (str(checkout_result.partner_code_id) if checkout_result.partner_code_id else None),
        "commission_contract_id": snapshot.get("commission_contract_id"),
        "owner_type": snapshot.get("owner_type"),
        "attribution_model": "last_eligible_touch",
    }
    if snapshot:
        policy_snapshot["commission_contract_snapshot"] = snapshot
    return policy_snapshot


def _optional_uuid(raw_value: object) -> UUID | None:
    if raw_value in (None, ""):
        return None
    return UUID(str(raw_value))


def _application_fx_conversion_id(application: dict) -> UUID | None:
    raw_value = application.get("fx_conversion_id")
    discount = application.get("discount")
    if raw_value in (None, "") and isinstance(discount, dict):
        raw_value = discount.get("fx_conversion_id")
    return _optional_uuid(raw_value)


async def _persist_fx_conversion_for_application(
    session: AsyncSession,
    application_model: CheckoutCodeApplicationModel,
    application: dict,
) -> None:
    if application_model.fx_conversion_id is not None:
        return
    if application_model.growth_code_id is None or application_model.policy_version_id is None:
        return
    discount = application.get("discount")
    if not isinstance(discount, dict):
        return
    fx_conversion = discount.get("fx_conversion")
    if not isinstance(fx_conversion, dict):
        return
    rate_snapshot = fx_conversion.get("rate_snapshot")
    rate_payload = rate_snapshot if isinstance(rate_snapshot, dict) else None
    fx_rate_snapshot_id = _optional_uuid(rate_payload.get("rate_id")) if rate_payload is not None else None
    if fx_rate_snapshot_id is not None and await session.get(FxRateSnapshotModel, fx_rate_snapshot_id) is None:
        fx_rate_snapshot_id = None

    source_amount = Decimal(str(fx_conversion["source_amount"]))
    target_currency = str(fx_conversion["target_currency"])
    raw_converted_amount = (
        source_amount * Decimal(str(rate_payload["rate"])) if rate_payload is not None else source_amount
    )
    model = FxDiscountConversionModel(
        code_application_id=application_model.id,
        growth_code_id=application_model.growth_code_id,
        policy_version_id=application_model.policy_version_id,
        source_amount=source_amount,
        source_currency=str(fx_conversion["source_currency"]),
        target_currency=target_currency,
        conversion_mode=str(fx_conversion.get("conversion_mode") or "same_currency"),
        fx_rate_snapshot_id=fx_rate_snapshot_id,
        configured_rate_version=(
            str(rate_payload.get("configured_rate_version"))
            if rate_payload is not None and rate_payload.get("configured_rate_version") not in (None, "")
            else None
        ),
        raw_converted_amount=raw_converted_amount,
        rounded_amount=Decimal(str(fx_conversion["target_amount"])),
        applied_amount=Decimal(str(fx_conversion["applied_amount"])),
        target_minor_units=minor_units_for_currency(target_currency),
        rounding_mode=str(fx_conversion.get("rounding_mode") or "ROUND_HALF_UP"),
    )
    session.add(model)
    await session.flush()
    conversion_id = str(model.id)
    application_model.fx_conversion_id = model.id
    discount["fx_conversion_id"] = conversion_id
    application["fx_conversion_id"] = conversion_id
    application["discount"] = discount
    application_model.discount_snapshot = dict(discount)
    await session.flush()


def _capacity_context_from_application(application: dict) -> ReservationCapacityContext:
    evaluation_trace = application.get("evaluation_trace")
    trace = evaluation_trace if isinstance(evaluation_trace, dict) else {}
    private_access = application.get("private_access")
    private_snapshot = private_access if isinstance(private_access, dict) else {}
    return ReservationCapacityContext(
        risk_subject_id=_optional_uuid(
            application.get("risk_subject_id")
            or trace.get("risk_subject_id")
            or private_snapshot.get("risk_subject_id")
        ),
        risk_decision_id=_optional_uuid(application.get("risk_decision_id") or trace.get("risk_decision_id")),
        device_key_hash=_optional_str(
            application.get("device_key_hash")
            or trace.get("device_key_hash")
            or private_snapshot.get("device_key_hash")
        ),
        velocity_bucket=_optional_str(application.get("velocity_bucket") or trace.get("velocity_bucket")),
    )


def _optional_str(raw_value: object) -> str | None:
    if raw_value in (None, ""):
        return None
    return str(raw_value)
