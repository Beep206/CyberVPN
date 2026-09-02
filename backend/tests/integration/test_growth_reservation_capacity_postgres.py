from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import asyncpg
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.use_cases.growth_codes.reservations import (
    GrowthCodeReservationError,
    GrowthCodeReservationService,
    ReservationCapacityContext,
)
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.growth_benefit_model import (
    GrowthCodeCapacityCounterModel,
    GrowthCodeUserCounterModel,
)
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeModel,
    GrowthCodeReservationModel,
    PromoCodePolicyModel,
)
from src.infrastructure.database.models.growth_code_set_model import (
    CheckoutCodeSetModel,
    GrowthCodeReservationGroupModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

CAPACITY_REVISION = "20260626_growth_res_capacity"
PREVIOUS_REVISION = "20260626_growth_reversals"
CURRENT_HEAD_REVISION = "20260901_partner_grant_exclusive"


@dataclass(frozen=True, slots=True)
class _ReservationSeed:
    user_ids: tuple[uuid.UUID, ...]
    code_ids: tuple[uuid.UUID, ...]
    risk_subject_id: uuid.UUID
    auth_realm_id: uuid.UUID


@pytest.mark.asyncio
async def test_postgres_growth_reservation_capacity_migration_clean_upgrade_downgrade_reupgrade() -> None:
    database_name = f"cvpn_growth_res_mig_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('growth_code_capacity_counters')") is not None
            reservation_columns = {
                row["column_name"]
                for row in await conn.fetch(
                    """
                    select column_name
                    from information_schema.columns
                    where table_name = 'growth_code_reservations'
                      and column_name = any($1::text[])
                    """,
                    [
                        "risk_subject_id",
                        "risk_decision_id",
                        "device_key_hash",
                        "velocity_bucket",
                        "capacity_context",
                    ],
                )
            }
            assert reservation_columns == {
                "risk_subject_id",
                "risk_decision_id",
                "device_key_hash",
                "velocity_bucket",
                "capacity_context",
            }
            current_revision = await conn.fetchval("select version_num from alembic_version")
            assert current_revision == CURRENT_HEAD_REVISION
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('growth_code_capacity_counters')") is None
            removed_count = await conn.fetchval(
                """
                select count(*)
                from information_schema.columns
                where table_name = 'growth_code_reservations'
                  and column_name = any($1::text[])
                """,
                [
                    "risk_subject_id",
                    "risk_decision_id",
                    "device_key_hash",
                    "velocity_bucket",
                    "capacity_context",
                ],
            )
            assert removed_count == 0
            current_revision = await conn.fetchval("select version_num from alembic_version")
            assert current_revision == PREVIOUS_REVISION
        finally:
            await conn.close()

        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        conn = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await conn.fetchval("select to_regclass('growth_code_capacity_counters')") is not None
            current_revision = await conn.fetchval("select version_num from alembic_version")
            assert current_revision == CURRENT_HEAD_REVISION
        finally:
            await conn.close()
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_opposite_order_reservations_do_not_deadlock_and_account_capacity() -> None:
    database_name = f"cvpn_growth_res_order_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        seed = await _seed_reservation_fixture(maker, code_count=2, user_count=2, max_uses=3)
        first_order = [seed.code_ids[0], seed.code_ids[1]]
        opposite_order = [seed.code_ids[1], seed.code_ids[0]]

        async def reserve_pair(user_id: uuid.UUID, code_ids: list[uuid.UUID]) -> list[uuid.UUID]:
            async with maker() as session:
                await session.execute(text("SET LOCAL lock_timeout = '2s'"))
                await session.execute(text("SET LOCAL statement_timeout = '8s'"))
                result = await GrowthCodeReservationService(session).reserve_many_for_quote(
                    growth_code_ids=code_ids,
                    quote_session_id=None,
                    user_id=user_id,
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                )
                await session.commit()
                return [result[code_id].id for code_id in code_ids]

        reservation_ids = await asyncio.wait_for(
            asyncio.gather(
                reserve_pair(seed.user_ids[0], first_order),
                reserve_pair(seed.user_ids[1], opposite_order),
            ),
            timeout=12,
        )
        assert len({item for batch in reservation_ids for item in batch}) == 4

        async with maker() as session:
            codes = (
                (
                    await session.execute(
                        select(GrowthCodeModel)
                        .where(GrowthCodeModel.id.in_(seed.code_ids))
                        .order_by(GrowthCodeModel.id)
                    )
                )
                .scalars()
                .all()
            )
            assert [code.reserved_uses for code in codes] == [2, 2]
            assert [code.uses_count for code in codes] == [0, 0]
            reservation_count = await session.scalar(select(func.count(GrowthCodeReservationModel.id)))
            assert reservation_count == 4
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_global_cap_race_allows_one_winner_without_over_reservation() -> None:
    database_name = f"cvpn_growth_res_global_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        seed = await _seed_reservation_fixture(maker, code_count=1, user_count=2, max_uses=1)
        code_id = seed.code_ids[0]

        async def reserve_once(user_id: uuid.UUID) -> str:
            async with maker() as session:
                await session.execute(text("SET LOCAL lock_timeout = '2s'"))
                try:
                    await GrowthCodeReservationService(session).reserve_many_for_quote(
                        growth_code_ids=[code_id],
                        quote_session_id=None,
                        user_id=user_id,
                        expires_at=datetime.now(UTC) + timedelta(minutes=30),
                    )
                except GrowthCodeReservationError as exc:
                    await session.rollback()
                    return exc.code
                await session.commit()
                return "reserved"

        results = await asyncio.wait_for(
            asyncio.gather(*(reserve_once(user_id) for user_id in seed.user_ids)),
            timeout=12,
        )
        assert sorted(results) == ["RESERVATION_GROUP_EXHAUSTED", "reserved"]

        async with maker() as session:
            code = await session.get(GrowthCodeModel, code_id)
            assert code is not None
            assert code.reserved_uses == 1
            assert code.uses_count == 0
            reservation_count = await session.scalar(select(func.count(GrowthCodeReservationModel.id)))
            assert reservation_count == 1
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_user_risk_device_velocity_caps_release_and_consume_accounting() -> None:
    database_name = f"cvpn_growth_res_caps_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        seed = await _seed_reservation_fixture(
            maker,
            code_count=1,
            user_count=2,
            max_uses=5,
            per_user_cap=1,
            policy_snapshot={"reservation_caps": {"risk_subject": 1, "device": 1, "velocity": 1}},
        )
        code_id = seed.code_ids[0]
        context = ReservationCapacityContext(
            risk_subject_id=seed.risk_subject_id,
            risk_decision_id=uuid.uuid4(),
            device_key_hash="device-hash-capacity-1",
            velocity_bucket="2026-06-26T00:00Z:customer-growth",
        )

        async with maker() as session:
            first_reservation = (
                await GrowthCodeReservationService(session).reserve_many_for_quote(
                    growth_code_ids=[code_id],
                    quote_session_id=None,
                    user_id=seed.user_ids[0],
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                    capacity_contexts={code_id: context},
                )
            )[code_id]
            await session.commit()

        same_user_result = await _reserve_and_return_code(maker, code_id, seed.user_ids[0], context)
        assert same_user_result == "PROMO_USER_USAGE_CAP_REACHED"
        same_risk_context = ReservationCapacityContext(
            risk_subject_id=seed.risk_subject_id,
            risk_decision_id=uuid.uuid4(),
            device_key_hash="device-hash-capacity-2",
            velocity_bucket="2026-06-26T01:00Z:customer-growth",
        )
        same_risk_result = await _reserve_and_return_code(maker, code_id, seed.user_ids[1], same_risk_context)
        assert same_risk_result == "RISK_SUBJECT_USAGE_CAP_REACHED"
        second_risk_subject_id = await _create_risk_subject(maker)
        same_device_context = ReservationCapacityContext(
            risk_subject_id=second_risk_subject_id,
            risk_decision_id=uuid.uuid4(),
            device_key_hash=context.device_key_hash,
            velocity_bucket="2026-06-26T02:00Z:customer-growth",
        )
        same_device_result = await _reserve_and_return_code(maker, code_id, seed.user_ids[1], same_device_context)
        assert same_device_result == "DEVICE_USAGE_CAP_REACHED"
        third_risk_subject_id = await _create_risk_subject(maker)
        same_velocity_context = ReservationCapacityContext(
            risk_subject_id=third_risk_subject_id,
            risk_decision_id=uuid.uuid4(),
            device_key_hash="device-hash-capacity-3",
            velocity_bucket=context.velocity_bucket,
        )
        same_velocity_result = await _reserve_and_return_code(maker, code_id, seed.user_ids[1], same_velocity_context)
        assert same_velocity_result == "VELOCITY_USAGE_CAP_REACHED"

        async with maker() as session:
            await GrowthCodeReservationService(session).release_reservation(
                reservation_id=first_reservation.id,
                reason="pytest_release_restore",
            )
            await session.commit()

        async with maker() as session:
            code = await session.get(GrowthCodeModel, code_id)
            assert code is not None
            assert code.reserved_uses == 0
            user_counter = await session.get(GrowthCodeUserCounterModel, (code_id, seed.user_ids[0]))
            assert user_counter is not None
            assert user_counter.reserved_uses == 0
            assert user_counter.consumed_uses == 0
            capacity_reserved = await session.scalar(
                select(func.coalesce(func.sum(GrowthCodeCapacityCounterModel.reserved_uses), 0)).where(
                    GrowthCodeCapacityCounterModel.growth_code_id == code_id
                )
            )
            assert capacity_reserved == 0

        async with maker() as session:
            reservation = (
                await GrowthCodeReservationService(session).reserve_many_for_quote(
                    growth_code_ids=[code_id],
                    quote_session_id=None,
                    user_id=seed.user_ids[1],
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                    capacity_contexts={code_id: context},
                )
            )[code_id]
            payment = PaymentModel(
                id=uuid.uuid4(),
                external_id=f"pytest-growth-capacity-{uuid.uuid4()}",
                user_uuid=seed.user_ids[1],
                amount=Decimal("1.00"),
                currency="USD",
                status="completed",
                provider="internal_zero",
                subscription_days=30,
                final_amount=Decimal("0"),
            )
            session.add(payment)
            await session.flush()
            consumed = await GrowthCodeReservationService(session).consume_for_payment(
                reservation_id=reservation.id,
                payment_id=payment.id,
                user_id=seed.user_ids[1],
            )
            await session.commit()
            assert consumed.consumed_payment_id == payment.id

        async with maker() as session:
            code = await session.get(GrowthCodeModel, code_id)
            assert code is not None
            assert code.reserved_uses == 0
            assert code.uses_count == 1
            user_counter = await session.get(GrowthCodeUserCounterModel, (code_id, seed.user_ids[1]))
            assert user_counter is not None
            assert user_counter.reserved_uses == 0
            assert user_counter.consumed_uses == 1
            capacity_consumed = await session.scalar(
                select(func.coalesce(func.sum(GrowthCodeCapacityCounterModel.consumed_uses), 0)).where(
                    GrowthCodeCapacityCounterModel.growth_code_id == code_id
                )
            )
            assert capacity_consumed == 3
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_group_replacement_releases_old_capacity_and_is_idempotent() -> None:
    database_name = f"cvpn_growth_res_replace_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        seed = await _seed_reservation_fixture(maker, code_count=2, user_count=1, max_uses=2)
        old_code_id, new_code_id = seed.code_ids
        user_id = seed.user_ids[0]
        expires_at = datetime.now(UTC) + timedelta(minutes=30)

        async with maker() as session:
            old_set = _checkout_code_set(seed, user_id=user_id, suffix="old")
            new_set = _checkout_code_set(seed, user_id=user_id, suffix="new")
            session.add_all([old_set, new_set])
            await session.flush()
            service = GrowthCodeReservationService(session)
            old_reservation = (
                await service.reserve_many_for_quote(
                    growth_code_ids=[old_code_id],
                    quote_session_id=None,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )[old_code_id]
            old_group = await service.create_group_for_quote(
                code_set_id=old_set.id,
                reservations=[old_reservation],
                user_id=user_id,
                quote_session_id=None,
                expires_at=expires_at,
                idempotency_key=f"pytest-growth-replace-old-{uuid.uuid4()}",
            )
            new_reservation = (
                await service.reserve_many_for_quote(
                    growth_code_ids=[new_code_id],
                    quote_session_id=None,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )[new_code_id]
            replacement_key = f"pytest-growth-replace-new-{uuid.uuid4()}"
            new_group = await service.replace_group_for_quote(
                old_group_id=old_group.id,
                code_set_id=new_set.id,
                reservations=[new_reservation],
                user_id=user_id,
                quote_session_id=None,
                expires_at=expires_at,
                idempotency_key=replacement_key,
            )
            retry_group = await service.replace_group_for_quote(
                old_group_id=old_group.id,
                code_set_id=new_set.id,
                reservations=[new_reservation],
                user_id=user_id,
                quote_session_id=None,
                expires_at=expires_at,
                idempotency_key=replacement_key,
            )
            await session.commit()
            assert retry_group.id == new_group.id

        async with maker() as session:
            old_code = await session.get(GrowthCodeModel, old_code_id)
            new_code = await session.get(GrowthCodeModel, new_code_id)
            assert old_code is not None
            assert new_code is not None
            assert old_code.reserved_uses == 0
            assert new_code.reserved_uses == 1
            old_group_db = await session.get(GrowthCodeReservationGroupModel, old_group.id)
            new_group_db = await session.get(GrowthCodeReservationGroupModel, new_group.id)
            old_reservation_db = await session.get(GrowthCodeReservationModel, old_reservation.id)
            new_reservation_db = await session.get(GrowthCodeReservationModel, new_reservation.id)
            assert old_group_db is not None
            assert new_group_db is not None
            assert old_reservation_db is not None
            assert new_reservation_db is not None
            assert old_group_db.status == "released"
            assert old_group_db.release_reason == "code_set_replaced"
            assert new_group_db.status == "reserved"
            assert old_reservation_db.status == "released"
            assert old_reservation_db.release_reason == "code_set_replaced"
            assert new_reservation_db.status == "reserved"
            assert new_reservation_db.reservation_group_id == new_group.id
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


async def _reserve_and_return_code(
    maker: async_sessionmaker[AsyncSession],
    code_id: uuid.UUID,
    user_id: uuid.UUID,
    context: ReservationCapacityContext,
) -> str:
    async with maker() as session:
        try:
            await GrowthCodeReservationService(session).reserve_many_for_quote(
                growth_code_ids=[code_id],
                quote_session_id=None,
                user_id=user_id,
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
                capacity_contexts={code_id: context},
            )
        except GrowthCodeReservationError as exc:
            await session.rollback()
            return exc.code
        await session.commit()
        return "reserved"


async def _create_risk_subject(maker: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async with maker() as session:
        risk_subject = RiskSubjectModel(
            id=uuid.uuid4(),
            principal_class="customer",
            principal_subject=f"growth-reservation-risk-extra-{uuid.uuid4()}",
            status="active",
            risk_level="low",
            metadata_payload={},
        )
        session.add(risk_subject)
        await session.commit()
        return risk_subject.id


async def _seed_reservation_fixture(
    maker: async_sessionmaker[AsyncSession],
    *,
    code_count: int,
    user_count: int,
    max_uses: int,
    per_user_cap: int | None = None,
    policy_snapshot: dict | None = None,
) -> _ReservationSeed:
    suffix = uuid.uuid4().hex[:12]
    async with maker() as session:
        auth_realm = AuthRealmModel(
            id=uuid.uuid4(),
            realm_key=f"gr-{suffix}",
            realm_type="customer",
            display_name=f"Growth Reservation {suffix}",
            audience=f"growth-reservation-{suffix}",
            cookie_namespace=f"gr_{suffix}",
        )
        users = [
            MobileUserModel(
                id=uuid.uuid4(),
                email=f"growth-reservation-{suffix}-{index}@example.test",
                password_hash="pytest-password-hash",
                is_active=True,
                status="active",
            )
            for index in range(user_count)
        ]
        codes: list[GrowthCodeModel] = []
        for index in range(code_count):
            codes.append(
                GrowthCodeModel(
                    id=uuid.uuid4(),
                    code_hash=f"pytest-growth-reservation-{suffix}-{index}",
                    code_prefix="PGR",
                    code_type="promo",
                    status="active",
                    issuer_type="admin",
                    max_uses=max_uses,
                    uses_count=0,
                    reserved_uses=0,
                )
            )
        risk_subject = RiskSubjectModel(
            id=uuid.uuid4(),
            principal_class="customer",
            principal_subject=f"growth-reservation-risk-{suffix}",
            status="active",
            risk_level="low",
            metadata_payload={},
        )
        session.add_all([auth_realm, *users, *codes, risk_subject])
        await session.flush()
        for code in codes:
            session.add(
                PromoCodePolicyModel(
                    id=uuid.uuid4(),
                    growth_code_id=code.id,
                    discount_type="percent",
                    discount_value=Decimal("10"),
                    max_discount_amount=None,
                    eligible_plan_ids=[],
                    eligible_plan_families=[],
                    eligible_durations=[],
                    eligible_addons=[],
                    allowed_checkout_modes=[],
                    allowed_channels=[],
                    allowed_geos=[],
                    min_net_paid_amount=None,
                    currency_code="USD",
                    discount_scope="order",
                    discountable_addon_codes=[],
                    minimum_order_amount=None,
                    allow_zero_amount_order=False,
                    new_customer_only=False,
                    first_completed_order_only=False,
                    first_net_paid_order_only=False,
                    require_no_active_access=False,
                    commission_basis="net_gateway_paid",
                    include_wallet_in_commission_base=False,
                    policy_version=1,
                    is_current=True,
                    published_at=datetime.now(UTC),
                    usage_cap_per_user=per_user_cap,
                    global_usage_cap=max_uses,
                    policy_snapshot=dict(policy_snapshot or {}),
                )
            )
        await session.commit()
        return _ReservationSeed(
            user_ids=tuple(user.id for user in users),
            code_ids=tuple(code.id for code in codes),
            risk_subject_id=risk_subject.id,
            auth_realm_id=auth_realm.id,
        )


def _checkout_code_set(seed: _ReservationSeed, *, user_id: uuid.UUID, suffix: str) -> CheckoutCodeSetModel:
    return CheckoutCodeSetModel(
        id=uuid.uuid4(),
        code_set_hash=f"pytest-growth-reservation-{suffix}-{uuid.uuid4()}",
        user_id=user_id,
        anonymous_session_id=None,
        auth_realm_id=seed.auth_realm_id,
        storefront_id=None,
        sale_channel="web",
        action_context="checkout",
        status="reserved",
        acceptance_mode="best_applicable",
        aggregate_result={},
        risk_snapshot={},
    )
