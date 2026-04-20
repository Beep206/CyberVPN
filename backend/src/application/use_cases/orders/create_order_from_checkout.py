from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.attribution.order_resolution import ResolveOrderAttributionUseCase
from src.application.use_cases.orders.snapshot_builder import build_order_item_payloads, build_order_snapshots
from src.infrastructure.database.models.order_model import OrderItemModel, OrderModel
from src.infrastructure.database.repositories.commerce_session_repo import CommerceSessionRepository
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.presentation.dependencies.auth_realms import RealmResolution


class CreateOrderFromCheckoutSessionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._checkout_repo = CommerceSessionRepository(session)
        self._orders = OrderRepository(session)
        self._outbox = EventOutboxService(session)

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
        if await self._orders.get_by_checkout_session_id(checkout_session_id) is not None:
            raise ValueError("Order already exists for this checkout session")

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
        settlement_status = "paid" if float(quote_snapshot.get("gateway_amount", 0)) <= 0 else "pending_payment"

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
            commission_base_amount=float(quote_snapshot.get("commission_base_amount", 0)),
            merchant_snapshot=merchant_snapshot,
            pricing_snapshot=pricing_snapshot,
            policy_snapshot=policy_snapshot,
            entitlements_snapshot=dict(quote_snapshot.get("entitlements_snapshot", {})),
        )
        created_order = await self._orders.create(order)
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
        if settlement_status == "paid":
            await self._outbox.append_event(
                event_name="order.finalized",
                aggregate_type="order",
                aggregate_id=str(created_order.id),
                partition_key=str(created_order.user_id),
                event_payload={
                    "order_id": str(created_order.id),
                    "settlement_status": created_order.settlement_status,
                    "source": "wallet_only_commit",
                },
                actor_context=OutboxActorContext(
                    principal_type="customer",
                    principal_id=str(created_order.user_id),
                    auth_realm_id=str(created_order.auth_realm_id),
                ),
                source_context={"source_use_case": "CreateOrderFromCheckoutSessionUseCase"},
            )
        resolver = ResolveOrderAttributionUseCase(self._session)
        await resolver.execute(order_id=created_order.id, commit=False)
        checkout_session.checkout_status = "committed"
        await self._session.commit()
        refreshed = await self._orders.get_by_id(created_order.id)
        if refreshed is None:
            raise ValueError("Order was created but could not be reloaded")
        return refreshed
