from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.use_cases.attribution.order_resolution.resolve_order_attribution import (
    ResolveOrderAttributionUseCase,
)
from src.infrastructure.database.models.order_attribution_result_model import OrderAttributionResultModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_postgres_concurrent_order_attribution_resolve_returns_single_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_name = f"cvpn_attr_race_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with maker() as session:
            order_id = await _seed_unowned_order(session)

        both_writers_ready = asyncio.Event()
        writer_count = 0
        writer_count_lock = asyncio.Lock()
        original_create = OrderAttributionResultRepository.create

        async def synchronized_create(
            self: OrderAttributionResultRepository,
            model: OrderAttributionResultModel,
        ) -> OrderAttributionResultModel:
            nonlocal writer_count
            async with writer_count_lock:
                writer_count += 1
                if writer_count == 2:
                    both_writers_ready.set()
            await asyncio.wait_for(both_writers_ready.wait(), timeout=5)
            return await original_create(self, model)

        monkeypatch.setattr(OrderAttributionResultRepository, "create", synchronized_create)

        async def resolve_once() -> uuid.UUID:
            async with maker() as session:
                result = await ResolveOrderAttributionUseCase(session).execute(order_id=order_id)
                return result.id

        first_result_id, second_result_id = await asyncio.wait_for(
            asyncio.gather(resolve_once(), resolve_once()),
            timeout=10,
        )

        assert first_result_id == second_result_id
        assert writer_count == 2
        async with maker() as session:
            result_count = await session.scalar(
                select(func.count())
                .select_from(OrderAttributionResultModel)
                .where(OrderAttributionResultModel.order_id == order_id)
            )
            finalized_event_count = await session.scalar(
                select(func.count())
                .select_from(OutboxEventModel)
                .where(OutboxEventModel.event_name == "attribution.result.finalized")
            )
        assert result_count == 1
        assert finalized_event_count == 1
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


async def _seed_unowned_order(session: AsyncSession) -> uuid.UUID:
    realm_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    storefront_id = uuid.uuid4()
    user_id = uuid.uuid4()
    quote_id = uuid.uuid4()
    checkout_id = uuid.uuid4()
    order_id = uuid.uuid4()
    unique_suffix = uuid.uuid4().hex[:8]
    params = {
        "realm_id": realm_id,
        "realm_key": f"race-{unique_suffix}",
        "audience": f"race-audience-{unique_suffix}",
        "cookie_namespace": f"race-{unique_suffix}",
        "brand_id": brand_id,
        "brand_key": f"race-brand-{unique_suffix}",
        "storefront_id": storefront_id,
        "storefront_key": f"race-store-{unique_suffix}",
        "host": f"race-{unique_suffix}.example.test",
        "user_id": user_id,
        "email": f"attr-race-{unique_suffix}@example.test",
        "public_uid": 70_000_000 + int(unique_suffix[:4], 16) % 20_000_000,
        "quote_id": quote_id,
        "checkout_id": checkout_id,
        "idempotency_key": f"attr-race-{unique_suffix}",
        "order_id": order_id,
    }
    await session.execute(
        text(
            """
            insert into auth_realms (
                id, realm_key, realm_type, display_name, audience, cookie_namespace, status, is_default
            )
            values (
                :realm_id, :realm_key, 'customer', 'Race Customer', :audience, :cookie_namespace, 'active', true
            )
            """
        ),
        params,
    )
    await session.execute(
        text(
            """
            insert into brands (id, brand_key, display_name, status)
            values (:brand_id, :brand_key, 'Race Brand', 'active')
            """
        ),
        params,
    )
    await session.execute(
        text(
            """
            insert into storefronts (id, storefront_key, brand_id, display_name, host, auth_realm_id, status)
            values (:storefront_id, :storefront_key, :brand_id, 'Race Store', :host, :realm_id, 'active')
            """
        ),
        params,
    )
    await session.execute(
        text(
            """
            insert into mobile_users (
                id, auth_realm_id, email, password_hash, is_active, status,
                is_partner, totp_enabled, notification_prefs, public_uid
            )
            values (
                :user_id, :realm_id, :email, 'hash', true, 'active',
                false, false, '{}', :public_uid
            )
            """
        ),
        params,
    )
    await session.execute(
        text(
            """
            insert into quote_sessions (
                id, user_id, auth_realm_id, storefront_id, request_snapshot, quote_snapshot,
                context_snapshot, expires_at
            )
            values (
                :quote_id, :user_id, :realm_id, :storefront_id, '{}', '{}', '{}', now() + interval '1 day'
            )
            """
        ),
        params,
    )
    await session.execute(
        text(
            """
            insert into checkout_sessions (
                id, quote_session_id, user_id, auth_realm_id, storefront_id, idempotency_key,
                request_snapshot, checkout_snapshot, context_snapshot, expires_at
            )
            values (
                :checkout_id, :quote_id, :user_id, :realm_id, :storefront_id, :idempotency_key,
                '{}', '{}', '{}', now() + interval '1 day'
            )
            """
        ),
        params,
    )
    await session.execute(
        text(
            """
            insert into orders (
                id, checkout_session_id, quote_session_id, user_id, auth_realm_id, storefront_id,
                base_price, displayed_price, gateway_amount, commission_base_amount,
                merchant_snapshot, pricing_snapshot, policy_snapshot, entitlements_snapshot
            )
            values (
                :order_id, :checkout_id, :quote_id, :user_id, :realm_id, :storefront_id,
                100.00, 100.00, 100.00, 100.00,
                '{}', '{}', '{}', '{}'
            )
            """
        ),
        params,
    )
    await session.commit()
    return order_id
