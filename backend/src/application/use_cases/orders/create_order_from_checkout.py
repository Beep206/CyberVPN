from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.attribution.order_resolution import ResolveOrderAttributionUseCase
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
        await self._persist_single_code_order_ledger(
            checkout_session=checkout_session,
            order=created_order,
            quote_snapshot=quote_snapshot,
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
        reservation_id = _extract_reservation_id(quote_snapshot)
        if reservation_id is not None:
            if is_zero_gateway:
                await self._reservations.commit_for_order(
                    reservation_id=reservation_id,
                    order_id=created_order.id,
                )
            else:
                await self._reservations.consume_for_order(
                    reservation_id=reservation_id,
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

    async def _persist_single_code_order_ledger(
        self,
        *,
        checkout_session,
        order: OrderModel,
        quote_snapshot: dict,
    ) -> None:
        code_resolution = dict(quote_snapshot.get("code_resolution") or {})
        growth_code_id = _uuid_or_none(code_resolution.get("growth_code_id"))
        if growth_code_id is None or code_resolution.get("accepted") is not True:
            return

        discount_snapshot = _matching_discount_snapshot(quote_snapshot)
        discount_amount = _decimal(
            discount_snapshot.get("amount") if discount_snapshot else quote_snapshot.get("discount_amount")
        )
        code_ref = _safe_code_ref(quote_snapshot, discount_snapshot)
        code_set_hash = _code_set_hash(code_ref=code_ref, growth_code_id=growth_code_id)
        reservation_id = _uuid_or_none(code_resolution.get("reservation_id"))
        policy_version_id = _uuid_or_none((discount_snapshot or {}).get("policy_version_id")) or _uuid_or_none(
            dict(code_resolution.get("policy_snapshot") or {}).get("policy_version_id")
        )
        application_role = str(
            code_resolution.get("code_type") or (discount_snapshot or {}).get("type") or "growth_code"
        )

        code_set = CheckoutCodeSetModel(
            code_set_hash=code_set_hash,
            user_id=checkout_session.user_id,
            anonymous_session_id=None,
            auth_realm_id=checkout_session.auth_realm_id,
            storefront_id=checkout_session.storefront_id,
            sale_channel=checkout_session.sale_channel,
            action_context=str(code_resolution.get("action_context") or "checkout"),
            status="consumed",
            acceptance_mode="single_legacy_code",
            aggregate_result={
                "snapshot_version": "checkout_code_set.single_legacy.v1",
                "accepted": True,
                "discount_amount": str(discount_amount),
                "currency_code": checkout_session.currency_code,
                "code_type": application_role,
                "code_ref": code_ref,
            },
            risk_snapshot={
                "risk_decision_id": code_resolution.get("risk_decision_id"),
                "reject_reason": code_resolution.get("reject_reason"),
            },
            private_access_grant_id=checkout_session.private_catalog_access_grant_id,
            quote_session_id=checkout_session.quote_session_id,
            checkout_session_id=checkout_session.id,
            order_id=order.id,
        )
        self._session.add(code_set)
        await self._session.flush()

        checkout_session.code_set_id = code_set.id
        order.code_set_id = code_set.id

        application_snapshot = {
            "snapshot_version": "order_code_application.single_legacy.v1",
            "code_ref": code_ref,
            "code_resolution": _safe_code_resolution_snapshot(code_resolution),
            "discount": discount_snapshot,
            "reservation_id": str(reservation_id) if reservation_id else None,
        }
        checkout_application = CheckoutCodeApplicationModel(
            code_set_id=code_set.id,
            position_entered=0,
            canonical_order=0,
            growth_code_id=growth_code_id,
            legacy_code_type=application_role,
            legacy_code_id=_uuid_or_none(code_resolution.get("promo_code_id"))
            or _uuid_or_none(code_resolution.get("partner_code_id")),
            masked_code=_masked_code(code_ref),
            roles={"primary": application_role, "source": "single_legacy_field"},
            resolution_status="accepted",
            reject_reason=None,
            conflict_code=code_resolution.get("conflict_code"),
            policy_version_id=policy_version_id,
            reservation_id=reservation_id,
            discount_snapshot=dict(discount_snapshot or {}),
            benefits_snapshot={},
            private_access_snapshot={},
            evaluation_trace={"source": "quote_snapshot", "schema_version": "single_legacy.v1"},
        )
        order_application = OrderCodeApplicationModel(
            order_id=order.id,
            code_set_id=code_set.id,
            growth_code_id=growth_code_id,
            policy_version_id=policy_version_id,
            application_role=application_role,
            application_status="applied",
            discount_amount=discount_amount,
            currency_code=checkout_session.currency_code,
            source_amount=discount_amount,
            source_currency_code=checkout_session.currency_code,
            reservation_id=reservation_id,
            application_snapshot=application_snapshot,
        )
        self._session.add_all([checkout_application, order_application])
        await self._session.flush()


def _extract_reservation_id(quote_snapshot: dict) -> UUID | None:
    code_resolution = dict(quote_snapshot.get("code_resolution") or {})
    raw_value = code_resolution.get("reservation_id")
    if not raw_value:
        return None
    return UUID(str(raw_value))


def _matching_discount_snapshot(quote_snapshot: dict) -> dict | None:
    discounts = quote_snapshot.get("discounts")
    if not isinstance(discounts, list):
        return None
    for discount in discounts:
        if isinstance(discount, dict) and Decimal(str(discount.get("amount") or "0")) > 0:
            return dict(discount)
    for discount in discounts:
        if isinstance(discount, dict):
            return dict(discount)
    return None


def _safe_code_ref(quote_snapshot: dict, discount_snapshot: dict | None) -> dict:
    for candidate in (
        (discount_snapshot or {}).get("code_ref"),
        quote_snapshot.get("code_input_ref"),
    ):
        if isinstance(candidate, dict):
            return {
                "redacted": bool(candidate.get("redacted", True)),
                "code_hash": candidate.get("code_hash"),
                "code_prefix": candidate.get("code_prefix"),
                "code_length": candidate.get("code_length"),
            }
    return {"redacted": True, "code_hash": None, "code_prefix": "***", "code_length": None}


def _safe_code_resolution_snapshot(code_resolution: dict) -> dict:
    allowed_keys = {
        "accepted",
        "code_type",
        "action_context",
        "result",
        "reject_reason",
        "wrong_context_target",
        "issuer_type",
        "owner_type",
        "growth_code_id",
        "promo_code_id",
        "partner_code_id",
        "reservation_id",
        "user_message_key",
        "policy_snapshot",
    }
    return {key: code_resolution.get(key) for key in allowed_keys if key in code_resolution}


def _masked_code(code_ref: dict) -> str:
    prefix = str(code_ref.get("code_prefix") or "***")[:12]
    code_hash = str(code_ref.get("code_hash") or "")
    suffix = code_hash[:12] if code_hash else "unknown"
    return f"{prefix}...{suffix}"[:32]


def _code_set_hash(*, code_ref: dict, growth_code_id: UUID) -> str:
    code_hash = code_ref.get("code_hash") or str(growth_code_id)
    return hashlib.sha256(f"single-legacy:{code_hash}".encode()).hexdigest()


def _decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def _uuid_or_none(value) -> UUID | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    return UUID(text)
