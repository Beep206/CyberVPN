from __future__ import annotations

import asyncio
import uuid

import asyncpg
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.gifts.provisioning import GiftProvisioningRequest, GiftProvisioningResult
from src.application.use_cases.gifts.service import RedeemGiftCodeUseCase
from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.growth_code_model import (
    GiftCodePolicyModel,
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel
from src.presentation.api.v1.gifts import routes as gift_routes
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _asyncpg_url_for_database,
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]

PREVIOUS_REVISION = "20260831_drop_receipts"
CURRENT_REVISION = "20260831_gift_redemption_safety"


class _SuccessfulGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def provision_gift_access(self, request: GiftProvisioningRequest) -> GiftProvisioningResult:
        self.calls += 1
        return GiftProvisioningResult(
            customer_account_id=request.customer_account_id,
            gift_code_id=request.gift_code_id,
            remnawave_uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, f"gift-race:{request.customer_account_id}")),
            remnawave_user_id=8_700_000 + self.calls,
            profile_id=request.profile_id,
            status="active",
            expires_at=request.access_expires_at,
            subscription_url="https://subscription.example.test/gift-race",
            created=True,
        )


class _AmbiguousGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def provision_gift_access(self, _request: GiftProvisioningRequest) -> GiftProvisioningResult:
        self.calls += 1
        raise RuntimeError("provider outcome unknown")


async def _seed_gift_race(
    maker: async_sessionmaker[AsyncSession],
) -> tuple[AuthRealmModel, uuid.UUID, tuple[uuid.UUID, uuid.UUID]]:
    realm_id = uuid.uuid4()
    gift_code_id = uuid.uuid4()
    user_ids = (uuid.uuid4(), uuid.uuid4())
    async with maker() as session:
        realm = AuthRealmModel(
            id=realm_id,
            realm_key=f"gift-race-{realm_id.hex[:12]}",
            realm_type="customer",
            display_name="Gift race realm",
            audience=f"gift-race-{realm_id}",
            cookie_namespace=f"gift_{realm_id.hex[:12]}",
            status="active",
            is_default=False,
        )
        session.add(realm)
        await session.flush()
        for index, user_id in enumerate(user_ids, start=1):
            session.add(
                MobileUserModel(
                    id=user_id,
                    public_uid=9_800_000 + index,
                    auth_realm_id=realm_id,
                    email=f"gift-race-{user_id}@example.test",
                    password_hash="not-used-in-concurrency-test",
                    is_active=True,
                    status="active",
                )
            )
        await session.flush()
        growth_code = GrowthCodeModel(
            id=gift_code_id,
            code_hash=hash_growth_code("GIFT-RACE-ONE-USE"),
            code_prefix="GIFT-RACE",
            code_type="gift",
            status="active",
            issuer_type="system",
            auth_realm_id=realm_id,
            max_uses=1,
            uses_count=0,
            reserved_uses=0,
            code_namespace="customer_input",
        )
        session.add(growth_code)
        await session.flush()
        session.add(
            GiftCodePolicyModel(
                growth_code_id=gift_code_id,
                grant_type="subscription_access",
                plan_family="pro",
                duration_days=30,
                entitlement_snapshot={
                    "plan_code": "pro",
                    "effective_entitlements": {"device_limit": 3, "traffic_limit_bytes": None},
                },
                redemption_mode="single_use",
                transferable=False,
                policy_snapshot={},
            )
        )
        await session.commit()
    return realm, gift_code_id, user_ids


async def _stage_and_provision(
    *,
    maker: async_sessionmaker[AsyncSession],
    realm_id: uuid.UUID,
    gift_code_id: uuid.UUID,
    user_id: uuid.UUID,
    current_realm: RealmResolution,
    gateway,
    barrier: asyncio.Barrier | None = None,
) -> str:
    async with maker() as session:
        await session.execute(text("SET LOCAL lock_timeout = '5s'"))
        await session.execute(text("SET LOCAL statement_timeout = '15s'"))
        if barrier is not None:
            await barrier.wait()
        try:
            result = await RedeemGiftCodeUseCase(session).execute(
                code="GIFT-RACE-ONE-USE",
                user_id=user_id,
                current_realm=current_realm,
            )
        except ValueError as exc:
            await session.rollback()
            assert "already redeemed" in str(exc).lower()
            return "conflict_409"
        assert result.growth_code.id == gift_code_id
        assert uuid.UUID(current_realm.realm_id) == realm_id
        try:
            await gift_routes.provision_redeemed_gift_access(
                db=session,
                user_id=user_id,
                result=result,
                provisioning_gateway=gateway,
            )
        except HTTPException:
            await session.rollback()
            return "conflict_409"
        await session.commit()
        return "redeemed"


@pytest.mark.asyncio
async def test_gift_redemption_migration_clean_upgrade_downgrade_reupgrade() -> None:
    database_name = f"cvpn_gift_safe_mig_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", CURRENT_REVISION)
        connection = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await connection.fetchval("select version_num from alembic_version") == CURRENT_REVISION
            assert (
                await connection.fetchval(
                    "select indexdef from pg_indexes where indexname = $1",
                    "uq_growth_code_redemptions_redeemed_gift",
                )
                is not None
            )
        finally:
            await connection.close()

        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        connection = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            assert await connection.fetchval("select version_num from alembic_version") == PREVIOUS_REVISION
            assert (
                await connection.fetchval(
                    "select indexdef from pg_indexes where indexname = $1",
                    "uq_growth_code_redemptions_redeemed_gift",
                )
                is None
            )
        finally:
            await connection.close()
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_gift_redemption_migration_fails_fast_on_populated_duplicate_claims() -> None:
    database_name = f"cvpn_gift_safe_dup_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        connection = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        growth_code_id = uuid.uuid4()
        try:
            await connection.execute(
                """
                insert into growth_codes (
                    id, code_hash, code_prefix, code_type, status, issuer_type,
                    max_uses, uses_count, reserved_uses, code_namespace, created_at, updated_at
                ) values ($1, $2, 'DUPGIFT', 'gift', 'redeemed', 'system', 1, 1, 0,
                          'customer_input', now(), now())
                """,
                growth_code_id,
                f"duplicate-{growth_code_id.hex}",
            )
            await connection.executemany(
                """
                insert into growth_code_redemptions (
                    id, growth_code_id, code_type, status, redeemed_at, created_at
                ) values ($1, $2, 'gift', 'redeemed', now(), now())
                """,
                [(uuid.uuid4(), growth_code_id), (uuid.uuid4(), growth_code_id)],
            )
        finally:
            await connection.close()

        failed = await asyncio.to_thread(_run_alembic, url, "upgrade", "head", False)
        assert failed.returncode != 0
        assert "Duplicate redeemed gift rows must be reconciled" in (failed.stdout + failed.stderr)

        connection = await asyncpg.connect(_asyncpg_url_for_database(database_name))
        try:
            await connection.execute(
                """
                delete from growth_code_redemptions
                where id in (
                    select id from growth_code_redemptions
                    where growth_code_id = $1
                    order by created_at, id
                    offset 1
                )
                """,
                growth_code_id,
            )
        finally:
            await connection.close()
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_concurrent_one_use_gift_calls_provider_and_persists_access_once(monkeypatch) -> None:
    database_name = f"cvpn_gift_safe_race_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        realm, gift_code_id, user_ids = await _seed_gift_race(maker)
        current_realm = RealmResolution(auth_realm=realm, source="test")
        monkeypatch.setattr(gift_routes, "AsyncSessionLocal", maker)
        gateway = _SuccessfulGateway()
        barrier = asyncio.Barrier(2)

        results = await asyncio.wait_for(
            asyncio.gather(
                *(
                    _stage_and_provision(
                        maker=maker,
                        realm_id=realm.id,
                        gift_code_id=gift_code_id,
                        user_id=user_id,
                        current_realm=current_realm,
                        gateway=gateway,
                        barrier=barrier,
                    )
                    for user_id in user_ids
                )
            ),
            timeout=20,
        )

        assert sorted(results) == ["conflict_409", "redeemed"]
        assert gateway.calls == 1
        async with maker() as session:
            assert await session.scalar(select(func.count(EntitlementGrantModel.id))) == 1
            assert await session.scalar(select(func.count(GrowthCodeRedemptionModel.id))) == 1
            persisted_code = await session.get(GrowthCodeModel, gift_code_id)
            assert persisted_code is not None
            assert persisted_code.status == "redeemed"
            assert persisted_code.uses_count == 1
            markers = (await session.execute(select(ApiIdempotencyRecordModel))).scalars().all()
            assert len(markers) == 2
            assert {marker.status for marker in markers} == {"completed"}
            assert {marker.response_payload["numeric_user_id"] for marker in markers} == {8_700_001}
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_ambiguous_gift_provider_outcome_blocks_second_customer(monkeypatch) -> None:
    database_name = f"cvpn_gift_safe_amb_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    engine = None
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        realm, gift_code_id, user_ids = await _seed_gift_race(maker)
        current_realm = RealmResolution(auth_realm=realm, source="test")
        monkeypatch.setattr(gift_routes, "AsyncSessionLocal", maker)
        gateway = _AmbiguousGateway()

        first = await _stage_and_provision(
            maker=maker,
            realm_id=realm.id,
            gift_code_id=gift_code_id,
            user_id=user_ids[0],
            current_realm=current_realm,
            gateway=gateway,
        )
        second = await _stage_and_provision(
            maker=maker,
            realm_id=realm.id,
            gift_code_id=gift_code_id,
            user_id=user_ids[1],
            current_realm=current_realm,
            gateway=gateway,
        )

        assert (first, second) == ("conflict_409", "conflict_409")
        assert gateway.calls == 1
        async with maker() as session:
            assert await session.scalar(select(func.count(EntitlementGrantModel.id))) == 0
            assert await session.scalar(select(func.count(GrowthCodeRedemptionModel.id))) == 0
            markers = (await session.execute(select(ApiIdempotencyRecordModel))).scalars().all()
            assert len(markers) == 2
            assert {marker.status for marker in markers} == {"reconciliation_required"}
    finally:
        if engine is not None:
            await engine.dispose()
        await _drop_database(database_name)
