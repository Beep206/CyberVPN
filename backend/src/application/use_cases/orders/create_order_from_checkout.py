from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.attribution.order_resolution import ResolveOrderAttributionUseCase
from src.application.use_cases.growth_code_sets.ledger import (
    accepted_code_set_applications,
    build_legacy_quote_application,
    build_order_code_application_snapshot,
    code_set_hash_for_applications,
    masked_code,
    matching_discount_snapshot,
    reservation_ids_from_snapshot,
    safe_code_ref,
)
from src.application.use_cases.growth_code_sets.snapshots import (
    SnapshotIntegrityError,
    validate_growth_checkout_integrity,
)
from src.application.use_cases.growth_codes.reservations import GrowthCodeReservationService
from src.application.use_cases.orders.snapshot_builder import build_order_item_payloads, build_order_snapshots
from src.infrastructure.database.models.growth_code_set_model import (
    CheckoutCodeApplicationModel,
    CheckoutCodeSetModel,
    OrderCodeApplicationModel,
)
from src.infrastructure.database.models.order_model import OrderItemModel, OrderModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.private_catalog_repo import SqlAlchemyPrivateCatalogRepository
from src.presentation.dependencies.auth_realms import RealmResolution


class CreateOrderFromCheckoutSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._checkout_repo = CommerceSessionRepository(session)
        self._orders = OrderRepository(session)
        self._outbox = EventOutboxService(session)
        self._reservations = GrowthCodeReservationService(session)
        self._private_catalog = SqlAlchemyPrivateCatalogRepository(session)

    @staticmethod
    def _normalize_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def execute(
        self,
        *,
        checkout_session_id: UUID,
        user_id: UUID,
        current_realm: RealmResolution,
    ) -> OrderModel:
        checkout_session = await self._checkout_repo.get_checkout_session_by_id(checkout_session_id)
        if checkout_session is None or checkout_session.user_id != user_id:
            raise ValueError("Checkout session not found")
        if str(checkout_session.auth_realm_id) != current_realm.realm_id:
            raise ValueError("Checkout session does not belong to the current auth realm")
        existing_order = await self._orders.get_by_checkout_session_id(checkout_session_id)
        if existing_order is not None:
            return existing_order

        checkout_expires_at = self._normalize_utc(checkout_session.expires_at)
        if checkout_expires_at <= datetime.now(UTC):
            checkout_session.checkout_status = "expired"
            await self._session.commit()
            raise ValueError("Checkout session has expired")

        quote_snapshot = dict((checkout_session.checkout_snapshot or {}).get("quote_snapshot", {}))
        context_snapshot = dict(checkout_session.context_snapshot or {})
        request_snapshot = dict(checkout_session.request_snapshot or {})
        merchant_snapshot, pricing_snapshot, policy_snapshot = build_order_snapshots(
            quote_snapshot=quote_snapshot,
            context_snapshot=context_snapshot,
            request_snapshot=request_snapshot,
        )
        try:
            validate_growth_checkout_integrity(quote_snapshot)
        except SnapshotIntegrityError as exc:
            raise ValueError("SNAPSHOT_INTEGRITY_ERROR") from exc
        is_zero_gateway = _decimal(quote_snapshot.get("gateway_amount")) <= Decimal("0")
        settlement_status = "pending_internal_settlement" if is_zero_gateway else "pending_payment"
        commission_base_amount = (
            Decimal("0") if is_zero_gateway else _decimal(quote_snapshot.get("commission_base_amount"))
        )

        order = OrderModel(
            quote_session_id=checkout_session.quote_session_id,
            checkout_session_id=checkout_session.id,
            user_id=checkout_session.user_id,
            auth_realm_id=checkout_session.auth_realm_id,
            storefront_id=checkout_session.storefront_id,
            merchant_profile_id=checkout_session.merchant_profile_id,
            invoice_profile_id=checkout_session.invoice_profile_id,
            billing_descriptor_id=checkout_session.billing_descriptor_id,
            pricebook_id=checkout_session.pricebook_id,
            pricebook_entry_id=checkout_session.pricebook_entry_id,
            offer_id=checkout_session.offer_id,
            legal_document_set_id=checkout_session.legal_document_set_id,
            program_eligibility_policy_id=checkout_session.program_eligibility_policy_id,
            subscription_plan_id=checkout_session.subscription_plan_id,
            promo_code_id=checkout_session.promo_code_id,
            partner_code_id=checkout_session.partner_code_id,
            private_catalog_access_grant_id=checkout_session.private_catalog_access_grant_id,
            sale_channel=checkout_session.sale_channel,
            currency_code=checkout_session.currency_code,
            order_status="committed",
            settlement_status=settlement_status,
            base_price=float(quote_snapshot.get("base_price", 0)),
            addon_amount=float(quote_snapshot.get("addon_amount", 0)),
            displayed_price=float(quote_snapshot.get("displayed_price", 0)),
            discount_amount=float(quote_snapshot.get("discount_amount", 0)),
            wallet_amount=float(quote_snapshot.get("wallet_amount", 0)),
            gateway_amount=float(quote_snapshot.get("gateway_amount", 0)),
            partner_markup=float(quote_snapshot.get("partner_markup", 0)),
            commission_base_amount=float(commission_base_amount),
            merchant_snapshot=merchant_snapshot,
            pricing_snapshot=pricing_snapshot,
            policy_snapshot=policy_snapshot,
            entitlements_snapshot=dict(quote_snapshot.get("entitlements_snapshot", {})),
        )
        created_order = await self._orders.create(order)
        await self._persist_order_code_ledger(
            checkout_session=checkout_session,
            order=created_order,
            quote_snapshot=quote_snapshot,
            growth_checkout_snapshot=pricing_snapshot.get("growth_checkout_snapshot") or {},
            is_zero_gateway=is_zero_gateway,
        )
        item_payloads = build_order_item_payloads(
            currency_code=checkout_session.currency_code,
            quote_snapshot=quote_snapshot,
            context_snapshot=context_snapshot,
        )
        await self._orders.create_items(
            [
                OrderItemModel(
                    order_id=created_order.id,
                    item_type=item_payload["item_type"],
                    subject_id=UUID(item_payload["subject_id"]) if item_payload["subject_id"] else None,
                    subject_code=item_payload["subject_code"],
                    display_name=item_payload["display_name"],
                    quantity=item_payload["quantity"],
                    unit_price=item_payload["unit_price"],
                    total_price=item_payload["total_price"],
                    currency_code=item_payload["currency_code"],
                    item_snapshot=item_payload["item_snapshot"],
                )
                for item_payload in item_payloads
            ]
        )
        await self._outbox.append_event(
            event_name="order.created",
            aggregate_type="order",
            aggregate_id=str(created_order.id),
            partition_key=str(created_order.user_id),
            event_payload={
                "order_id": str(created_order.id),
                "checkout_session_id": str(created_order.checkout_session_id),
                "quote_session_id": str(created_order.quote_session_id) if created_order.quote_session_id else None,
                "storefront_id": str(created_order.storefront_id),
                "auth_realm_id": str(created_order.auth_realm_id),
                "sale_channel": created_order.sale_channel,
                "currency_code": created_order.currency_code,
                "displayed_price": float(created_order.displayed_price),
                "gateway_amount": float(created_order.gateway_amount),
                "wallet_amount": float(created_order.wallet_amount),
                "settlement_status": created_order.settlement_status,
                "zero_payment_id": None,
                "zero_payment_attempt_id": None,
            },
            actor_context=OutboxActorContext(
                principal_type="customer",
                principal_id=str(created_order.user_id),
                auth_realm_id=str(created_order.auth_realm_id),
            ),
            source_context={
                "source_use_case": "CreateOrderFromCheckoutSessionUseCase",
                "checkout_session_id": str(created_order.checkout_session_id),
            },
        )
        resolver = ResolveOrderAttributionUseCase(self._session)
        await resolver.execute(order_id=created_order.id, commit=False)
        reservation_ids = reservation_ids_from_snapshot(quote_snapshot)
        fallback_reservation_id = _extract_reservation_id(quote_snapshot)
        if fallback_reservation_id is not None and fallback_reservation_id not in reservation_ids:
            reservation_ids.append(fallback_reservation_id)
        if reservation_ids:
            if is_zero_gateway:
                await self._reservations.commit_group_for_order(
                    reservation_ids=reservation_ids,
                    order_id=created_order.id,
                )
            else:
                await self._reservations.consume_group_for_order(
                    reservation_ids=reservation_ids,
                    order_id=created_order.id,
                )
        if checkout_session.private_catalog_access_grant_id is not None:
            await self._private_catalog.consume_grant_for_order(
                grant_id=checkout_session.private_catalog_access_grant_id,
                order_id=created_order.id,
            )
        checkout_session.checkout_status = "committed"
        await self._session.commit()
        refreshed = await self._orders.get_by_id(created_order.id)
        if refreshed is None:
            raise ValueError("Order was created but could not be reloaded")
        return refreshed

    async def _persist_order_code_ledger(
        self,
        *,
        checkout_session,
        order: OrderModel,
        quote_snapshot: dict[str, Any],
        growth_checkout_snapshot: dict[str, Any],
        is_zero_gateway: bool,
    ) -> None:
        applications = accepted_code_set_applications(growth_checkout_snapshot)
        if not applications:
            legacy_application = build_legacy_quote_application(quote_snapshot)
            applications = [legacy_application] if legacy_application is not None else []
        if not applications:
            return

        code_set = await self._load_or_create_code_set(
            checkout_session=checkout_session,
            order=order,
            applications=applications,
            is_zero_gateway=is_zero_gateway,
        )

        checkout_session.code_set_id = code_set.id
        order.code_set_id = code_set.id

        for application in applications:
            growth_code_id = _uuid_or_none(application.get("growth_code_id"))
            if growth_code_id is None:
                continue
            await self._ensure_checkout_application(
                code_set=code_set,
                application=application,
                growth_code_id=growth_code_id,
            )
            discount = dict(application.get("discount") or {})
            discount_amount = _decimal(discount.get("applied_amount"))
            fx_conversion_id = application.get("fx_conversion_id") or discount.get("fx_conversion_id")
            role = _application_role(application)
            order_application = OrderCodeApplicationModel(
                order_id=order.id,
                code_set_id=code_set.id,
                growth_code_id=growth_code_id,
                policy_version_id=_uuid_or_none(application.get("policy_version_id")),
                application_role=role,
                application_status="applied",
                discount_amount=discount_amount,
                currency_code=str(discount.get("target_currency") or checkout_session.currency_code),
                source_amount=_decimal_or_none(discount.get("source_amount")) or discount_amount,
                source_currency_code=str(discount.get("source_currency") or checkout_session.currency_code),
                fx_conversion_id=_uuid_or_none(fx_conversion_id),
                reservation_id=_uuid_or_none(application.get("reservation_id")),
                risk_decision_id=_uuid_or_none(application.get("risk_decision_id")),
                application_snapshot=build_order_code_application_snapshot(
                    application=dict(application),
                    reservation_group_id=growth_checkout_snapshot.get("reservation_group_id"),
                    producer="cybervpn-backend.order_code_ledger",
                ),
            )
            self._session.add(order_application)
        await self._session.flush()

    async def _load_or_create_code_set(
        self,
        *,
        checkout_session,
        order: OrderModel,
        applications: list[dict[str, Any]],
        is_zero_gateway: bool,
    ) -> CheckoutCodeSetModel:
        if checkout_session.code_set_id is not None:
            existing = await self._session.get(CheckoutCodeSetModel, checkout_session.code_set_id)
            if existing is not None:
                existing.checkout_session_id = checkout_session.id
                existing.order_id = order.id
                existing.status = "committed" if is_zero_gateway else "consumed"
                return existing

        code_set = CheckoutCodeSetModel(
            code_set_hash=code_set_hash_for_applications(applications),
            user_id=checkout_session.user_id,
            anonymous_session_id=None,
            auth_realm_id=checkout_session.auth_realm_id,
            storefront_id=checkout_session.storefront_id,
            sale_channel=checkout_session.sale_channel,
            action_context="checkout",
            status="committed" if is_zero_gateway else "consumed",
            acceptance_mode="single_legacy_code" if len(applications) == 1 else "all_or_nothing",
            aggregate_result={
                "snapshot_version": "checkout_code_set.v6",
                "accepted": True,
                "application_count": len(applications),
                "currency_code": checkout_session.currency_code,
            },
            risk_snapshot={
                "risk_decision_ids": [
                    str(application["risk_decision_id"])
                    for application in applications
                    if application.get("risk_decision_id")
                ],
            },
            private_access_grant_id=checkout_session.private_catalog_access_grant_id,
            quote_session_id=checkout_session.quote_session_id,
            checkout_session_id=checkout_session.id,
            order_id=order.id,
        )
        self._session.add(code_set)
        await self._session.flush()
        return code_set

    async def _ensure_checkout_application(
        self,
        *,
        code_set: CheckoutCodeSetModel,
        application: dict[str, Any],
        growth_code_id: UUID,
    ) -> None:
        existing = await self._session.execute(
            select(CheckoutCodeApplicationModel).where(
                CheckoutCodeApplicationModel.code_set_id == code_set.id,
                CheckoutCodeApplicationModel.growth_code_id == growth_code_id,
            )
        )
        if existing.scalars().first() is not None:
            return
        role = _application_role(application)
        self._session.add(
            CheckoutCodeApplicationModel(
                code_set_id=code_set.id,
                position_entered=int(application.get("position_entered") or 0),
                canonical_order=int(application.get("canonical_order") or 0),
                growth_code_id=growth_code_id,
                legacy_code_type=str(application.get("legacy_code_type") or role),
                legacy_code_id=_uuid_or_none(application.get("legacy_code_id")),
                masked_code=str(application.get("masked_code") or ""),
                roles={"values": list(application.get("roles") or []), "source": "code_set_snapshot"},
                resolution_status=str(application.get("status") or "accepted"),
                reject_reason=None,
                conflict_code=application.get("conflict_code"),
                policy_version_id=_uuid_or_none(application.get("policy_version_id")),
                risk_decision_id=_uuid_or_none(application.get("risk_decision_id")),
                fx_conversion_id=_uuid_or_none(
                    application.get("fx_conversion_id")
                    or dict(application.get("discount") or {}).get("fx_conversion_id")
                ),
                reservation_id=_uuid_or_none(application.get("reservation_id")),
                discount_snapshot=dict(application.get("discount") or {}),
                benefits_snapshot={"items": list(application.get("benefits") or [])},
                private_access_snapshot=dict(application.get("private_access") or {}),
                evaluation_trace=dict(application.get("evaluation_trace") or {}),
            )
        )


def _extract_reservation_id(quote_snapshot: dict) -> UUID | None:
    code_resolution = dict(quote_snapshot.get("code_resolution") or {})
    raw_value = code_resolution.get("reservation_id")
    if not raw_value:
        return None
    return UUID(str(raw_value))


def _legacy_application_from_quote(quote_snapshot: dict[str, Any]) -> dict[str, Any] | None:
    code_resolution = dict(quote_snapshot.get("code_resolution") or {})
    growth_code_id = _uuid_or_none(code_resolution.get("growth_code_id"))
    if growth_code_id is None or code_resolution.get("accepted") is not True:
        return None
    discount_snapshot = matching_discount_snapshot(quote_snapshot) or {}
    code_ref = safe_code_ref(quote_snapshot, discount_snapshot)
    role = str(code_resolution.get("code_type") or discount_snapshot.get("type") or "growth_code")
    discount_amount = str(discount_snapshot.get("amount") or quote_snapshot.get("discount_amount") or "0")
    return {
        "position_entered": 0,
        "canonical_order": 0,
        "growth_code_id": str(growth_code_id),
        "masked_code": masked_code(code_ref),
        "roles": [role],
        "status": "accepted",
        "policy_version_id": discount_snapshot.get("policy_version_id")
        or dict(code_resolution.get("policy_snapshot") or {}).get("policy_version_id"),
        "discount": {
            "source_amount": discount_amount,
            "source_currency": quote_snapshot.get("currency_code"),
            "target_amount": discount_amount,
            "target_currency": quote_snapshot.get("currency_code"),
            "applied_amount": discount_amount,
        },
        "benefits": list(dict(code_resolution.get("policy_snapshot") or {}).get("benefits") or []),
        "reservation_id": code_resolution.get("reservation_id"),
        "risk_decision_id": code_resolution.get("risk_decision_id"),
        "code_ref": code_ref,
        "legacy_code_type": role,
        "legacy_code_id": code_resolution.get("promo_code_id") or code_resolution.get("partner_code_id"),
        "evaluation_trace": {"source": "quote_snapshot", "schema_version": "single_legacy.v1"},
    }


def _application_role(application: dict[str, Any]) -> str:
    roles = application.get("roles")
    if isinstance(roles, list) and roles:
        return str(roles[0])
    return str(application.get("legacy_code_type") or "growth_code")


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or "0"))


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    return UUID(text)
