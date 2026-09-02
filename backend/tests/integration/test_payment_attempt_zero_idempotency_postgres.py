from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import asyncpg
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.payment_attempts.create_payment_attempt import (
    CreatePaymentAttemptResult,
    CreatePaymentAttemptUseCase,
)
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.checkout_session_model import CheckoutSessionModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.quote_session_model import QuoteSessionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

PREVIOUS_REVISION = "20260625_internal_status"
HARDENING_INDEXES = {
    "uq_payment_attempts_order_attempt_number",
    "uq_payment_attempts_order_active",
    "uq_payment_attempts_order_succeeded",
    "uq_payments_internal_zero_external_id",
}
HARDENING_CONSTRAINTS = {
    "ck_payments_internal_zero_external_id_required",
}


class FakeCryptoBotClient:
    def __init__(self) -> None:
        self.invoice_calls: list[dict[str, str | None]] = []
        self._counter = 5000

    async def create_invoice(self, amount: str, currency: str, description: str, payload: str | None = None) -> dict:
        self.invoice_calls.append(
            {
                "amount": amount,
                "currency": currency,
                "description": description,
                "payload": payload,
            }
        )
        await asyncio.sleep(0.05)
        self._counter += 1
        invoice_id = str(self._counter)
        return {
            "invoice_id": invoice_id,
            "pay_url": f"https://pay.example.test/{invoice_id}",
            "status": "pending",
            "expiration_date": "2030-01-01T00:00:00+00:00",
        }


@pytest.mark.asyncio
async def test_postgres_payment_attempt_creation_serializes_before_provider_side_effects() -> None:
    database_name = f"cvpn_pay_attempt_lock_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            same_key_order = await _seed_payable_order_fixture(maker)
            same_key_crypto = FakeCryptoBotClient()

            same_key_results = await asyncio.gather(
                _execute_payment_attempt(
                    maker,
                    order_id=same_key_order["order_id"],
                    user_id=same_key_order["user_id"],
                    auth_realm_id=same_key_order["auth_realm_id"],
                    idempotency_key="same-key",
                    crypto_client=same_key_crypto,
                ),
                _execute_payment_attempt(
                    maker,
                    order_id=same_key_order["order_id"],
                    user_id=same_key_order["user_id"],
                    auth_realm_id=same_key_order["auth_realm_id"],
                    idempotency_key="same-key",
                    crypto_client=same_key_crypto,
                ),
            )
            assert {result.payment_attempt.id for result in same_key_results} == {
                same_key_results[0].payment_attempt.id
            }
            assert sorted(result.created for result in same_key_results) == [False, True]
            assert len(same_key_crypto.invoice_calls) == 1
            assert await _payment_attempt_count(maker, order_id=same_key_order["order_id"]) == 1
            assert await _payment_count_for_order(maker, order_id=same_key_order["order_id"]) == 1

            different_key_order = await _seed_payable_order_fixture(maker)
            different_key_crypto = FakeCryptoBotClient()
            different_key_results = await asyncio.gather(
                _execute_payment_attempt(
                    maker,
                    order_id=different_key_order["order_id"],
                    user_id=different_key_order["user_id"],
                    auth_realm_id=different_key_order["auth_realm_id"],
                    idempotency_key="first-key",
                    crypto_client=different_key_crypto,
                ),
                _execute_payment_attempt(
                    maker,
                    order_id=different_key_order["order_id"],
                    user_id=different_key_order["user_id"],
                    auth_realm_id=different_key_order["auth_realm_id"],
                    idempotency_key="second-key",
                    crypto_client=different_key_crypto,
                ),
                return_exceptions=True,
            )
            created_results = [
                result for result in different_key_results if isinstance(result, CreatePaymentAttemptResult)
            ]
            conflicts = [result for result in different_key_results if isinstance(result, ValueError)]
            assert len(created_results) == 1
            assert len(conflicts) == 1
            assert "active payment attempt" in str(conflicts[0])
            assert len(different_key_crypto.invoice_calls) == 1
            assert await _payment_attempt_count(maker, order_id=different_key_order["order_id"]) == 1
            assert await _payment_count_for_order(maker, order_id=different_key_order["order_id"]) == 1

            zero_order_id, zero_user_id, zero_realm_id = await _seed_zero_gateway_order_fixture(maker)
            zero_crypto = FakeCryptoBotClient()
            zero_results = await asyncio.gather(
                _execute_payment_attempt(
                    maker,
                    order_id=zero_order_id,
                    user_id=zero_user_id,
                    auth_realm_id=zero_realm_id,
                    idempotency_key="zero-key",
                    crypto_client=zero_crypto,
                ),
                _execute_payment_attempt(
                    maker,
                    order_id=zero_order_id,
                    user_id=zero_user_id,
                    auth_realm_id=zero_realm_id,
                    idempotency_key="zero-key",
                    crypto_client=zero_crypto,
                ),
            )
            assert {result.payment_attempt.id for result in zero_results} == {zero_results[0].payment_attempt.id}
            assert sorted(result.created for result in zero_results) == [False, True]
            assert zero_crypto.invoice_calls == []
            assert await _payment_attempt_count(maker, order_id=zero_order_id) == 1
            assert await _payment_count_for_order(maker, order_id=zero_order_id) == 1
        finally:
            await engine.dispose()
    finally:
        await _drop_database(database_name)


@pytest.mark.parametrize(
    ("scenario", "expected_message"),
    [
        ("duplicate_attempt_number", "attempt-number uniqueness"),
        ("duplicate_active_attempts", "active-attempt uniqueness"),
        ("duplicate_succeeded_attempts", "succeeded-attempt uniqueness"),
        ("duplicate_internal_zero_external_id", "external-reference uniqueness"),
        ("null_internal_zero_external_id", "NULL external_id"),
    ],
)
@pytest.mark.asyncio
async def test_postgres_payment_attempt_idempotency_migration_rejects_invalid_existing_rows(
    scenario: str,
    expected_message: str,
) -> None:
    database_name = f"cvpn_pay_attempt_bad_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)

        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            order_id, user_id = await _seed_order_fixture(maker)
            await _seed_invalid_existing_state(
                maker,
                scenario=scenario,
                order_id=order_id,
                user_id=user_id,
            )
        finally:
            await engine.dispose()

        result = await asyncio.to_thread(_run_alembic, url, "upgrade", "head", False)
        assert result.returncode != 0
        assert expected_message in (result.stdout + result.stderr)
        assert HARDENING_INDEXES.isdisjoint(await _index_names(database_name))
        assert HARDENING_CONSTRAINTS.isdisjoint(await _constraint_names(database_name))
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_payment_attempt_idempotency_migration_upgrade_downgrade_reupgrade() -> None:
    database_name = f"cvpn_pay_attempt_idem_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        assert HARDENING_INDEXES.issubset(await _index_names(database_name))
        assert HARDENING_CONSTRAINTS.issubset(await _constraint_names(database_name))

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        assert HARDENING_INDEXES.isdisjoint(await _index_names(database_name))
        assert HARDENING_CONSTRAINTS.isdisjoint(await _constraint_names(database_name))

        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            order_id, user_id = await _seed_order_fixture(maker)
            await _seed_valid_existing_attempt_and_payment(maker, order_id=order_id, user_id=user_id)
        finally:
            await engine.dispose()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        assert HARDENING_INDEXES.issubset(await _index_names(database_name))
        assert HARDENING_CONSTRAINTS.issubset(await _constraint_names(database_name))

        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            await _assert_payment_attempt_indexes_block_duplicates(maker, order_id=order_id)
            await _assert_internal_zero_payment_index_blocks_duplicates(
                maker,
                order_id=order_id,
                user_id=user_id,
            )
        finally:
            await engine.dispose()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        assert HARDENING_INDEXES.isdisjoint(await _index_names(database_name))
        assert HARDENING_CONSTRAINTS.isdisjoint(await _constraint_names(database_name))

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        assert HARDENING_INDEXES.issubset(await _index_names(database_name))
        assert HARDENING_CONSTRAINTS.issubset(await _constraint_names(database_name))
    finally:
        await _drop_database(database_name)


async def _seed_order_fixture(
    maker: async_sessionmaker[AsyncSession],
) -> tuple[uuid.UUID, uuid.UUID]:
    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:10]
    async with maker() as session:
        customer_realm_id = await session.scalar(
            select(AuthRealmModel.id).where(AuthRealmModel.realm_key == "customer")
        )
        assert customer_realm_id is not None

        user_id = uuid.uuid4()
        # This seed is also used after downgrading to PREVIOUS_REVISION.  Insert
        # only columns present at that historical schema instead of asking the
        # current ORM mapper to write post-Remnawave expand columns.
        await session.execute(
            text(
                """
                INSERT INTO mobile_users (
                    id,
                    public_uid,
                    auth_realm_id,
                    email,
                    password_hash,
                    notification_prefs,
                    totp_enabled,
                    is_active,
                    status,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    :public_uid,
                    :auth_realm_id,
                    :email,
                    :password_hash,
                    CAST(:notification_prefs AS json),
                    false,
                    true,
                    'active',
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": user_id,
                "public_uid": 900_000_000 + (int(suffix, 16) % 99_999_999),
                "auth_realm_id": customer_realm_id,
                "email": f"payment-attempt-idem-{suffix}@example.test",
                "password_hash": "hash",
                "notification_prefs": "{}",
                "created_at": now,
                "updated_at": now,
            },
        )
        brand = BrandModel(
            id=uuid.uuid4(),
            brand_key=f"payment-attempt-idem-{suffix}",
            display_name="Payment Attempt Idempotency",
            status="active",
        )
        storefront = StorefrontModel(
            id=uuid.uuid4(),
            storefront_key=f"payment-attempt-idem-{suffix}",
            brand_id=brand.id,
            display_name="Payment Attempt Idempotency",
            host=f"payment-attempt-idem-{suffix}.example.test",
            auth_realm_id=customer_realm_id,
            status="active",
        )
        session.add_all([brand, storefront])
        await session.flush()

        quote = QuoteSessionModel(
            id=uuid.uuid4(),
            user_id=user_id,
            auth_realm_id=customer_realm_id,
            storefront_id=storefront.id,
            sale_channel="web",
            currency_code="USD",
            quote_status="open",
            request_snapshot={},
            quote_snapshot={},
            context_snapshot={},
            expires_at=now + timedelta(hours=1),
        )
        session.add(quote)
        await session.flush()

        checkout = CheckoutSessionModel(
            id=uuid.uuid4(),
            quote_session_id=quote.id,
            user_id=user_id,
            auth_realm_id=customer_realm_id,
            storefront_id=storefront.id,
            sale_channel="web",
            currency_code="USD",
            checkout_status="open",
            idempotency_key=f"payment-attempt-idem-checkout-{suffix}",
            request_snapshot={},
            checkout_snapshot={},
            context_snapshot={},
            expires_at=now + timedelta(hours=1),
        )
        session.add(checkout)
        await session.flush()

        order = OrderModel(
            id=uuid.uuid4(),
            quote_session_id=quote.id,
            checkout_session_id=checkout.id,
            user_id=user_id,
            auth_realm_id=customer_realm_id,
            storefront_id=storefront.id,
            sale_channel="web",
            currency_code="USD",
            order_status="committed",
            settlement_status="pending_internal_settlement",
            base_price=Decimal("0.00"),
            addon_amount=Decimal("0.00"),
            displayed_price=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            wallet_amount=Decimal("0.00"),
            gateway_amount=Decimal("0.00"),
            partner_markup=Decimal("0.00"),
            commission_base_amount=Decimal("0.00"),
            merchant_snapshot={},
            pricing_snapshot={},
            policy_snapshot={},
            risk_snapshot={},
            fx_snapshot={},
            entitlements_snapshot={},
        )
        session.add(order)
        await session.commit()
        return order.id, user_id


async def _seed_zero_gateway_order_fixture(
    maker: async_sessionmaker[AsyncSession],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    order_id, user_id = await _seed_order_fixture(maker)
    async with maker() as session:
        order = await session.get(OrderModel, order_id)
        assert order is not None
        return order_id, user_id, order.auth_realm_id


async def _seed_payable_order_fixture(
    maker: async_sessionmaker[AsyncSession],
) -> dict[str, uuid.UUID]:
    order_id, user_id, auth_realm_id = await _seed_zero_gateway_order_fixture(maker)
    plan_id = uuid.uuid4()
    async with maker() as session:
        session.add(
            SubscriptionPlanModel(
                id=plan_id,
                name=f"Concurrency Plan {plan_id}",
                display_name="Concurrency Plan",
                catalog_visibility="visible",
                catalog_access_class="public",
                duration_days=30,
                price_usd=Decimal("42.00"),
                sale_channels=["web"],
                is_active=True,
            )
        )
        await session.commit()

    async with maker() as session:
        order = await session.get(OrderModel, order_id)
        assert order is not None
        order.subscription_plan_id = plan_id
        order.settlement_status = "pending_payment"
        order.base_price = Decimal("42.00")
        order.displayed_price = Decimal("42.00")
        order.gateway_amount = Decimal("42.00")
        order.commission_base_amount = Decimal("42.00")
        order.pricing_snapshot = {
            "quote": {
                "base_price": "42.00",
                "addon_amount": "0.00",
                "displayed_price": "42.00",
                "discount_amount": "0.00",
                "wallet_amount": "0.00",
                "gateway_amount": "42.00",
                "partner_markup": "0.00",
                "commission_base_amount": "42.00",
                "is_zero_gateway": False,
                "plan_id": str(plan_id),
                "plan_name": "Concurrency Plan",
                "duration_days": 30,
                "addons": [],
                "entitlements_snapshot": {},
            }
        }
        await session.commit()
    return {
        "order_id": order_id,
        "user_id": user_id,
        "auth_realm_id": auth_realm_id,
    }


async def _execute_payment_attempt(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
    auth_realm_id: uuid.UUID,
    idempotency_key: str,
    crypto_client: FakeCryptoBotClient,
) -> CreatePaymentAttemptResult:
    async with maker() as session:
        realm = await session.get(AuthRealmModel, auth_realm_id)
        assert realm is not None
        return await CreatePaymentAttemptUseCase(session, crypto_client).execute(
            order_id=order_id,
            user_id=user_id,
            current_realm=RealmResolution(auth_realm=realm, source="test"),
            idempotency_key=idempotency_key,
        )


async def _payment_attempt_count(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
) -> int:
    async with maker() as session:
        value = await session.scalar(
            select(func.count()).select_from(PaymentAttemptModel).where(PaymentAttemptModel.order_id == order_id)
        )
        return int(value or 0)


async def _payment_count_for_order(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
) -> int:
    async with maker() as session:
        value = await session.scalar(
            select(func.count())
            .select_from(PaymentModel)
            .where(PaymentModel.metadata_["order_id"].as_string() == str(order_id))
        )
        return int(value or 0)


async def _seed_valid_existing_attempt_and_payment(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    async with maker() as session:
        session.add(
            PaymentAttemptModel(
                id=uuid.uuid4(),
                order_id=order_id,
                attempt_number=1,
                provider="cryptobot",
                sale_channel="web",
                currency_code="USD",
                status="failed",
                displayed_amount=0,
                wallet_amount=0,
                gateway_amount=0,
                external_reference="existing-failed-attempt",
                idempotency_key="existing-failed-attempt",
                provider_snapshot={},
                request_snapshot={},
                terminal_at=datetime.now(UTC),
            )
        )
        session.add(
            PaymentModel(
                id=uuid.uuid4(),
                external_id=f"internal_zero:{order_id}",
                user_uuid=user_id,
                amount=0,
                currency="USD",
                status="completed",
                provider="internal_zero",
                subscription_days=0,
                discount_amount=0,
                wallet_amount_used=0,
                final_amount=0,
                addons_snapshot=[],
                entitlements_snapshot={},
                growth_snapshot={},
                metadata_={},
            )
        )
        await session.commit()


async def _seed_invalid_existing_state(
    maker: async_sessionmaker[AsyncSession],
    *,
    scenario: str,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    if scenario == "duplicate_attempt_number":
        await _seed_attempts(
            maker,
            order_id=order_id,
            rows=[
                ("failed", 1, "duplicate-attempt-number-a"),
                ("expired", 1, "duplicate-attempt-number-b"),
            ],
        )
        return

    if scenario == "duplicate_active_attempts":
        await _seed_attempts(
            maker,
            order_id=order_id,
            rows=[
                ("pending", 1, "duplicate-active-a"),
                ("processing", 2, "duplicate-active-b"),
            ],
        )
        return

    if scenario == "duplicate_succeeded_attempts":
        await _seed_attempts(
            maker,
            order_id=order_id,
            rows=[
                ("succeeded", 1, "duplicate-succeeded-a"),
                ("succeeded", 2, "duplicate-succeeded-b"),
            ],
        )
        return

    if scenario == "duplicate_internal_zero_external_id":
        await _seed_payments(
            maker,
            user_id=user_id,
            external_ids=[f"internal_zero:{order_id}", f"internal_zero:{order_id}"],
        )
        return

    if scenario == "null_internal_zero_external_id":
        await _seed_payments(maker, user_id=user_id, external_ids=[None])
        return

    raise AssertionError(f"Unknown invalid migration scenario: {scenario}")


async def _seed_attempts(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
    rows: list[tuple[str, int, str]],
) -> None:
    async with maker() as session:
        for status, attempt_number, idempotency_key in rows:
            session.add(
                PaymentAttemptModel(
                    id=uuid.uuid4(),
                    order_id=order_id,
                    attempt_number=attempt_number,
                    provider="cryptobot",
                    sale_channel="web",
                    currency_code="USD",
                    status=status,
                    displayed_amount=0,
                    wallet_amount=0,
                    gateway_amount=0,
                    idempotency_key=idempotency_key,
                    provider_snapshot={},
                    request_snapshot={},
                    terminal_at=datetime.now(UTC) if status not in {"pending", "processing"} else None,
                )
            )
        await session.commit()


async def _seed_payments(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
    external_ids: list[str | None],
) -> None:
    async with maker() as session:
        for index, external_id in enumerate(external_ids):
            session.add(
                PaymentModel(
                    id=uuid.uuid4(),
                    external_id=external_id,
                    user_uuid=user_id,
                    amount=0,
                    currency="USD",
                    status="completed",
                    provider="internal_zero",
                    subscription_days=0,
                    discount_amount=0,
                    wallet_amount_used=0,
                    final_amount=0,
                    addons_snapshot=[],
                    entitlements_snapshot={},
                    growth_snapshot={},
                    metadata_={"seed_index": index},
                )
            )
        await session.commit()


async def _assert_payment_attempt_indexes_block_duplicates(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
) -> None:
    async with maker() as session:
        session.add(
            PaymentAttemptModel(
                id=uuid.uuid4(),
                order_id=order_id,
                attempt_number=1,
                provider="cryptobot",
                sale_channel="web",
                currency_code="USD",
                status="failed",
                displayed_amount=0,
                wallet_amount=0,
                gateway_amount=0,
                idempotency_key="duplicate-attempt-number",
                provider_snapshot={},
                request_snapshot={},
                terminal_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        await session.rollback()
        assert _constraint_name(exc_info.value) == "uq_payment_attempts_order_attempt_number"

        session.add(
            PaymentAttemptModel(
                id=uuid.uuid4(),
                order_id=order_id,
                attempt_number=2,
                provider="cryptobot",
                sale_channel="web",
                currency_code="USD",
                status="pending",
                displayed_amount=0,
                wallet_amount=0,
                gateway_amount=0,
                idempotency_key="active-attempt-1",
                provider_snapshot={},
                request_snapshot={},
            )
        )
        await session.commit()

        session.add(
            PaymentAttemptModel(
                id=uuid.uuid4(),
                order_id=order_id,
                attempt_number=3,
                provider="cryptobot",
                sale_channel="web",
                currency_code="USD",
                status="processing",
                displayed_amount=0,
                wallet_amount=0,
                gateway_amount=0,
                idempotency_key="active-attempt-2",
                provider_snapshot={},
                request_snapshot={},
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        await session.rollback()
        assert _constraint_name(exc_info.value) == "uq_payment_attempts_order_active"

        active_attempt = await session.scalar(
            select(PaymentAttemptModel).where(
                PaymentAttemptModel.order_id == order_id,
                PaymentAttemptModel.idempotency_key == "active-attempt-1",
            )
        )
        assert active_attempt is not None
        active_attempt.status = "failed"
        active_attempt.terminal_at = datetime.now(UTC)
        await session.commit()

        session.add(
            PaymentAttemptModel(
                id=uuid.uuid4(),
                order_id=order_id,
                attempt_number=3,
                provider="internal_zero",
                sale_channel="web",
                currency_code="USD",
                status="succeeded",
                displayed_amount=0,
                wallet_amount=0,
                gateway_amount=0,
                idempotency_key="succeeded-attempt-1",
                provider_snapshot={},
                request_snapshot={},
                terminal_at=datetime.now(UTC),
            )
        )
        await session.commit()

        session.add(
            PaymentAttemptModel(
                id=uuid.uuid4(),
                order_id=order_id,
                attempt_number=4,
                provider="internal_zero",
                sale_channel="web",
                currency_code="USD",
                status="succeeded",
                displayed_amount=0,
                wallet_amount=0,
                gateway_amount=0,
                idempotency_key="succeeded-attempt-2",
                provider_snapshot={},
                request_snapshot={},
                terminal_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        await session.rollback()
        assert _constraint_name(exc_info.value) == "uq_payment_attempts_order_succeeded"


async def _assert_internal_zero_payment_index_blocks_duplicates(
    maker: async_sessionmaker[AsyncSession],
    *,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    external_id = f"internal_zero:{order_id}"
    async with maker() as session:
        session.add(
            PaymentModel(
                id=uuid.uuid4(),
                external_id=external_id,
                user_uuid=user_id,
                amount=0,
                currency="USD",
                status="pending",
                provider="cryptobot",
                subscription_days=0,
                discount_amount=0,
                wallet_amount_used=0,
                final_amount=0,
                addons_snapshot=[],
                entitlements_snapshot={},
                growth_snapshot={},
                metadata_={},
            )
        )
        await session.commit()

        session.add(
            PaymentModel(
                id=uuid.uuid4(),
                external_id=external_id,
                user_uuid=user_id,
                amount=0,
                currency="USD",
                status="completed",
                provider="internal_zero",
                subscription_days=0,
                discount_amount=0,
                wallet_amount_used=0,
                final_amount=0,
                addons_snapshot=[],
                entitlements_snapshot={},
                growth_snapshot={},
                metadata_={},
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        await session.rollback()
        assert _constraint_name(exc_info.value) == "uq_payments_internal_zero_external_id"

        session.add(
            PaymentModel(
                id=uuid.uuid4(),
                external_id=None,
                user_uuid=user_id,
                amount=0,
                currency="USD",
                status="completed",
                provider="internal_zero",
                subscription_days=0,
                discount_amount=0,
                wallet_amount_used=0,
                final_amount=0,
                addons_snapshot=[],
                entitlements_snapshot={},
                growth_snapshot={},
                metadata_={},
            )
        )
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        await session.rollback()
        assert _constraint_name(exc_info.value) == "ck_payments_internal_zero_external_id_required"


async def _index_names(database_name: str) -> set[str]:
    conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
    try:
        rows = await conn.fetch(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = ANY($1::text[])
            """,
            sorted(HARDENING_INDEXES),
        )
        return {row["indexname"] for row in rows}
    finally:
        await conn.close()


async def _constraint_names(database_name: str) -> set[str]:
    conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
    try:
        rows = await conn.fetch(
            """
            SELECT conname
            FROM pg_constraint
            WHERE connamespace = 'public'::regnamespace
              AND conname = ANY($1::text[])
            """,
            sorted(HARDENING_CONSTRAINTS),
        )
        return {row["conname"] for row in rows}
    finally:
        await conn.close()


def _constraint_name(error: IntegrityError) -> str | None:
    original = error.orig
    diag = getattr(original, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name is not None:
        return str(constraint_name)
    cause = getattr(original, "__cause__", None)
    constraint_name = getattr(cause, "constraint_name", None)
    if constraint_name is not None:
        return str(constraint_name)
    details = str(error)
    for index_name in HARDENING_INDEXES | HARDENING_CONSTRAINTS:
        if index_name in details:
            return index_name
    return None
