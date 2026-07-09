from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.partner_attribution.attribution import (
    CapturePartnerAttributionCommand,
    CapturePartnerAttributionUseCase,
    ClaimPartnerAttributionCommand,
    ClaimPartnerAttributionResult,
    ClaimPartnerAttributionUseCase,
    ConsumePartnerAttributionTransferCommand,
    ConsumePartnerAttributionTransferUseCase,
    PartnerAttributionError,
)
from src.application.use_cases.partner_attribution.utils import hash_partner_attribution_token
from src.config import settings
from src.domain.enums import CustomerCommercialBindingStatus, CustomerCommercialBindingType
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.customer_commercial_binding_model import CustomerCommercialBindingModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.models.partner_attribution_session_model import PartnerAttributionSessionModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)

pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
HARDENING_REVISION = "20260621_partner_attr_hardening"
PREVIOUS_REVISION = "20260620_partner_attr_remaining"

_ACTIVE_OWNER_INDEXES = frozenset(
    {
        "uq_customer_commercial_bindings_active_owner_global_scope",
        "uq_customer_commercial_bindings_active_owner_storefront_scope",
    }
)


@pytest.fixture(autouse=True)
def _enable_partner_attribution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "partner_attribution_enabled", True)
    monkeypatch.setattr(settings, "partner_codes_enabled", True)


@pytest_asyncio.fixture
async def pg_sessionmaker() -> async_sessionmaker[AsyncSession]:
    url = os.getenv("CYBERVPN_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("CYBERVPN_TEST_POSTGRES_URL is required for PostgreSQL claim concurrency tests")

    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            if conn.dialect.name != "postgresql":
                pytest.skip("PostgreSQL dialect is required for claim concurrency tests")
            index_rows = await conn.execute(
                text(
                    """
                    select indexname
                    from pg_indexes
                    where schemaname = 'public'
                      and tablename = 'customer_commercial_bindings'
                      and indexname = any(:index_names)
                    """
                ),
                {"index_names": list(_ACTIVE_OWNER_INDEXES)},
            )
            present_indexes = set(index_rows.scalars().all())
            if present_indexes != _ACTIVE_OWNER_INDEXES:
                pytest.skip(f"Partner active-owner indexes are not installed: {sorted(present_indexes)}")

        yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    finally:
        await engine.dispose()


@dataclass(frozen=True)
class _ClaimSeed:
    realm: AuthRealmModel
    customer_id: uuid.UUID
    brand_id: uuid.UUID
    storefront_ids: list[uuid.UUID]
    owner_ids: list[uuid.UUID]
    account_ids: list[uuid.UUID]
    code_ids: list[uuid.UUID]
    session_ids: list[uuid.UUID]
    cookie_tokens: list[str]


async def _seed_claim_fixture(
    maker: async_sessionmaker[AsyncSession],
    *,
    same_owner: bool,
    session_count: int = 2,
) -> _ClaimSeed:
    suffix = uuid.uuid4().hex
    now = datetime.now(UTC)
    realm = AuthRealmModel(
        id=uuid.uuid4(),
        realm_key=f"pg-claim-{suffix}",
        realm_type="customer",
        display_name=f"PG Claim {suffix}",
        audience=f"cybervpn:pg-claim:{suffix}",
        cookie_namespace=f"pgclaim{suffix[:16]}",
        status="active",
        is_default=False,
    )
    customer = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=realm.id,
        email=f"pg-claim-customer-{suffix}@example.test",
        password_hash="hashed-password",
        is_active=True,
        status="active",
        created_at=now,
    )
    brand = BrandModel(
        id=uuid.uuid4(),
        brand_key=f"pg-claim-brand-{suffix[:24]}",
        display_name=f"PG Claim Brand {suffix[:12]}",
        status="active",
    )
    storefronts = [
        StorefrontModel(
            id=uuid.uuid4(),
            storefront_key=f"pg-claim-sf-{index}-{suffix[:22]}",
            brand_id=brand.id,
            display_name=f"PG Claim Storefront {index}",
            host=f"pg-claim-{index}-{suffix}.example.test",
            auth_realm_id=realm.id,
            status="active",
        )
        for index in range(2)
    ]

    owner_total = 1 if same_owner else session_count
    owners: list[MobileUserModel] = []
    accounts: list[PartnerAccountModel] = []
    codes: list[PartnerCodeModel] = []
    for index in range(owner_total):
        owner = MobileUserModel(
            id=uuid.uuid4(),
            auth_realm_id=realm.id,
            email=f"pg-claim-owner-{index}-{suffix}@example.test",
            password_hash="hashed-password",
            is_active=True,
            status="active",
            created_at=now,
        )
        account = PartnerAccountModel(
            id=uuid.uuid4(),
            account_key=f"pg-claim-acct-{index}-{suffix[:16]}",
            display_name=f"PG Claim Account {index}",
            status="active",
            legacy_owner_user_id=owner.id,
        )
        code = PartnerCodeModel(
            id=uuid.uuid4(),
            code=f"PGCL{index}{suffix[:18]}".upper(),
            code_normalized=f"PGCL{index}{suffix[:18]}".upper(),
            public_slug=f"pg-claim-code-{index}-{suffix}",
            public_token_hash=hash_partner_attribution_token(f"pg-claim-code-{index}-{suffix}"),
            partner_account_id=account.id,
            partner_user_id=owner.id,
            markup_pct=7,
            is_active=True,
            lifecycle_status="active",
            approval_status="approved",
            owner_type="affiliate",
            lane_key="creator_affiliate",
            attribution_model="last_eligible_touch",
            attribution_window_seconds=30 * 24 * 60 * 60,
            allowed_channels=["content"],
            allowed_storefront_ids=["*"],
            allowed_geographies=["*"],
            sub_id_schema={},
        )
        owners.append(owner)
        accounts.append(account)
        codes.append(code)

    sessions: list[PartnerAttributionSessionModel] = []
    cookie_tokens: list[str] = []
    for index in range(session_count):
        code = codes[0] if same_owner else codes[index]
        cookie_token = f"pg-claim-cookie-{index}-{suffix}"
        cookie_tokens.append(cookie_token)
        sessions.append(
            PartnerAttributionSessionModel(
                id=uuid.uuid4(),
                session_token_hash=hash_partner_attribution_token(cookie_token),
                transfer_token_hash=None,
                transfer_expires_at=None,
                partner_code_id=code.id,
                partner_account_id=code.partner_account_id,
                auth_realm_id=realm.id,
                storefront_id=None,
                status="transferred",
                owner_type="affiliate",
                attribution_model="last_eligible_touch",
                policy_version_id=None,
                commission_contract_id=None,
                source_host="cyber-vpn.net",
                source_path=f"/p/pg-claim-{index}",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={},
                click_id=None,
                browser_key_hash=None,
                capture_idempotency_key_hash=None,
                destination_url="/pricing",
                campaign_params={},
                evidence_payload={},
                policy_snapshot={},
                expires_at=now + timedelta(days=7),
                first_seen_at=now,
                last_seen_at=now,
                transferred_at=now,
            )
        )

    async with maker() as session:
        session.add_all([realm, brand, *storefronts, customer, *owners, *accounts])
        await session.flush()
        session.add_all(codes)
        await session.flush()
        session.add_all(sessions)
        await session.commit()

    return _ClaimSeed(
        realm=realm,
        customer_id=customer.id,
        brand_id=brand.id,
        storefront_ids=[storefront.id for storefront in storefronts],
        owner_ids=[owner.id for owner in owners],
        account_ids=[account.id for account in accounts],
        code_ids=[code.id for code in codes],
        session_ids=[item.id for item in sessions],
        cookie_tokens=cookie_tokens,
    )


@dataclass(frozen=True)
class _CaptureSeed:
    realm: AuthRealmModel
    owner_id: uuid.UUID
    account_id: uuid.UUID
    code_id: uuid.UUID
    public_slug: str


async def _seed_capture_fixture(maker: async_sessionmaker[AsyncSession]) -> _CaptureSeed:
    suffix = uuid.uuid4().hex
    now = datetime.now(UTC)
    realm = AuthRealmModel(
        id=uuid.uuid4(),
        realm_key=f"pg-capture-{suffix}",
        realm_type="customer",
        display_name=f"PG Capture {suffix}",
        audience=f"cybervpn:pg-capture:{suffix}",
        cookie_namespace=f"pgcapture{suffix[:16]}",
        status="active",
        is_default=False,
    )
    owner = MobileUserModel(
        id=uuid.uuid4(),
        auth_realm_id=realm.id,
        email=f"pg-capture-owner-{suffix}@example.test",
        password_hash="hashed-password",
        is_active=True,
        status="active",
        created_at=now,
    )
    account = PartnerAccountModel(
        id=uuid.uuid4(),
        account_key=f"pg-capture-acct-{suffix[:16]}",
        display_name=f"PG Capture Account {suffix[:12]}",
        status="active",
        legacy_owner_user_id=owner.id,
    )
    public_slug = f"pg-capture-code-{suffix}"
    code = PartnerCodeModel(
        id=uuid.uuid4(),
        code=f"PGCAP{suffix[:18]}".upper(),
        code_normalized=f"PGCAP{suffix[:18]}".upper(),
        public_slug=public_slug,
        public_token_hash=hash_partner_attribution_token(public_slug),
        partner_account_id=account.id,
        partner_user_id=owner.id,
        markup_pct=7,
        is_active=True,
        lifecycle_status="active",
        approval_status="approved",
        owner_type="affiliate",
        lane_key="creator_affiliate",
        attribution_model="last_eligible_touch",
        attribution_window_seconds=30 * 24 * 60 * 60,
        allowed_channels=["content"],
        allowed_storefront_ids=["*"],
        allowed_geographies=["*"],
        sub_id_schema={},
    )
    async with maker() as session:
        session.add_all([realm, owner, account])
        await session.flush()
        session.add(code)
        await session.commit()
    return _CaptureSeed(
        realm=realm,
        owner_id=owner.id,
        account_id=account.id,
        code_id=code.id,
        public_slug=public_slug,
    )


@pytest.mark.asyncio
async def test_capture_idempotency_key_is_reused_under_parallel_first_loads(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    seed = await _seed_capture_fixture(pg_sessionmaker)
    current_realm = RealmResolution(auth_realm=seed.realm, source="test")
    browser_key = f"pg-browser-key-{uuid.uuid4()}"
    idempotency_key = f"pg-capture-idempotency-{uuid.uuid4()}"
    start = asyncio.Event()

    async def capture_once() -> tuple[uuid.UUID, str]:
        async with pg_sessionmaker() as session:
            await start.wait()
            result = await CapturePartnerAttributionUseCase(session).execute(
                CapturePartnerAttributionCommand(
                    public_token=seed.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/pg-capture",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={"creator": "pg"},
                    click_id="pg-click",
                    browser_key=browser_key,
                    capture_idempotency_key=idempotency_key,
                    campaign_params={"utm_source": "pg"},
                    current_realm=current_realm,
                )
            )
            await session.commit()
            return result.attribution_id, result.transfer_token

    first = asyncio.create_task(capture_once())
    second = asyncio.create_task(capture_once())
    await asyncio.sleep(0)
    start.set()
    first_result, second_result = await asyncio.gather(first, second)

    assert first_result == second_result
    async with pg_sessionmaker() as session:
        session_count = await session.scalar(
            select(func.count())
            .select_from(PartnerAttributionSessionModel)
            .where(PartnerAttributionSessionModel.partner_code_id == seed.code_id)
        )
        touchpoint_count = await session.scalar(
            select(func.count())
            .select_from(AttributionTouchpointModel)
            .where(AttributionTouchpointModel.partner_code_id == seed.code_id)
        )
        capture_event_count = await session.scalar(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(
                OutboxEventModel.event_name == "partner.attribution.captured",
                OutboxEventModel.aggregate_id == str(first_result[0]),
            )
        )
    assert session_count == 1
    assert touchpoint_count == 1
    assert capture_event_count == 1


@pytest.mark.asyncio
async def test_capture_same_browser_link_can_reclick_after_transfer(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    seed = await _seed_capture_fixture(pg_sessionmaker)
    current_realm = RealmResolution(auth_realm=seed.realm, source="test")
    browser_key = f"pg-reclick-browser-key-{uuid.uuid4()}"
    idempotency_key = f"pg-reclick-idempotency-{uuid.uuid4()}"

    async with pg_sessionmaker() as session:
        first_capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-reclick",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=idempotency_key,
                campaign_params={"utm_source": "pg"},
                current_realm=current_realm,
            )
        )
        await ConsumePartnerAttributionTransferUseCase(session).execute(
            ConsumePartnerAttributionTransferCommand(transfer_token=first_capture.transfer_token)
        )
        await session.commit()

    async with pg_sessionmaker() as session:
        second_capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-reclick",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=idempotency_key,
                campaign_params={"utm_source": "pg"},
                current_realm=current_realm,
            )
        )
        await session.commit()

    assert second_capture.attribution_id != first_capture.attribution_id
    idempotency_hash = hash_partner_attribution_token(idempotency_key)
    async with pg_sessionmaker() as session:
        rows = (
            await session.execute(
                select(
                    PartnerAttributionSessionModel.id,
                    PartnerAttributionSessionModel.status,
                    PartnerAttributionSessionModel.transfer_consumed_at,
                    PartnerAttributionSessionModel.capture_idempotency_key_hash,
                    PartnerAttributionSessionModel.destination_url,
                )
                .where(PartnerAttributionSessionModel.partner_code_id == seed.code_id)
                .order_by(PartnerAttributionSessionModel.created_at.asc())
            )
        ).all()

    assert [row.id for row in rows] == [first_capture.attribution_id, second_capture.attribution_id]
    assert rows[0].status == "transferred"
    assert rows[0].transfer_consumed_at is not None
    assert rows[0].capture_idempotency_key_hash is None
    assert rows[1].capture_idempotency_key_hash == idempotency_hash
    assert "pat=" not in rows[0].destination_url
    assert "pat=" not in rows[1].destination_url
    assert first_capture.transfer_token not in rows[0].destination_url
    assert second_capture.transfer_token not in rows[1].destination_url


@pytest.mark.asyncio
async def test_capture_same_browser_link_can_reclick_after_expiry(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    seed = await _seed_capture_fixture(pg_sessionmaker)
    current_realm = RealmResolution(auth_realm=seed.realm, source="test")
    browser_key = f"pg-expired-browser-key-{uuid.uuid4()}"
    idempotency_key = f"pg-expired-idempotency-{uuid.uuid4()}"

    async with pg_sessionmaker() as session:
        first_capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-expired",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=idempotency_key,
                campaign_params={"utm_source": "pg"},
                current_realm=current_realm,
            )
        )
        expired_at = datetime.now(UTC) - timedelta(seconds=5)
        await session.execute(
            text(
                """
                update partner_attribution_sessions
                set expires_at = :expired_at
                where id = :session_id
                """
            ),
            {"expired_at": expired_at, "session_id": first_capture.attribution_id},
        )
        await session.commit()

    async with pg_sessionmaker() as session:
        second_capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-expired",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=idempotency_key,
                campaign_params={"utm_source": "pg"},
                current_realm=current_realm,
            )
        )
        await session.commit()

    assert second_capture.attribution_id != first_capture.attribution_id
    idempotency_hash = hash_partner_attribution_token(idempotency_key)
    async with pg_sessionmaker() as session:
        rows = (
            await session.execute(
                select(
                    PartnerAttributionSessionModel.id,
                    PartnerAttributionSessionModel.expires_at,
                    PartnerAttributionSessionModel.capture_idempotency_key_hash,
                    PartnerAttributionSessionModel.destination_url,
                )
                .where(PartnerAttributionSessionModel.partner_code_id == seed.code_id)
                .order_by(PartnerAttributionSessionModel.created_at.asc())
            )
        ).all()

    assert [row.id for row in rows] == [first_capture.attribution_id, second_capture.attribution_id]
    assert rows[0].expires_at < datetime.now(UTC)
    assert rows[0].capture_idempotency_key_hash is None
    assert rows[1].capture_idempotency_key_hash == idempotency_hash
    assert "pat=" not in rows[0].destination_url
    assert "pat=" not in rows[1].destination_url


@pytest.mark.asyncio
async def test_capture_same_browser_link_can_reclick_after_transfer_token_expiry(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    seed = await _seed_capture_fixture(pg_sessionmaker)
    current_realm = RealmResolution(auth_realm=seed.realm, source="test")
    browser_key = f"pg-transfer-expired-browser-key-{uuid.uuid4()}"
    idempotency_key = f"pg-transfer-expired-idempotency-{uuid.uuid4()}"

    async with pg_sessionmaker() as session:
        first_capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-transfer-expired",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=idempotency_key,
                campaign_params={"utm_source": "pg"},
                current_realm=current_realm,
            )
        )
        expired_at = datetime.now(UTC) - timedelta(seconds=5)
        await session.execute(
            text(
                """
                update partner_attribution_sessions
                set transfer_expires_at = :expired_at
                where id = :session_id
                """
            ),
            {"expired_at": expired_at, "session_id": first_capture.attribution_id},
        )
        await session.commit()

    async with pg_sessionmaker() as session:
        second_capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-transfer-expired",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=idempotency_key,
                campaign_params={"utm_source": "pg"},
                current_realm=current_realm,
            )
        )
        transfer = await ConsumePartnerAttributionTransferUseCase(session).execute(
            ConsumePartnerAttributionTransferCommand(transfer_token=second_capture.transfer_token)
        )
        await session.commit()

    assert second_capture.attribution_id != first_capture.attribution_id
    assert transfer.attribution_id == second_capture.attribution_id
    idempotency_hash = hash_partner_attribution_token(idempotency_key)
    async with pg_sessionmaker() as session:
        rows = (
            await session.execute(
                select(
                    PartnerAttributionSessionModel.id,
                    PartnerAttributionSessionModel.transfer_expires_at,
                    PartnerAttributionSessionModel.capture_idempotency_key_hash,
                    PartnerAttributionSessionModel.destination_url,
                )
                .where(PartnerAttributionSessionModel.partner_code_id == seed.code_id)
                .order_by(PartnerAttributionSessionModel.created_at.asc())
            )
        ).all()

    assert [row.id for row in rows] == [first_capture.attribution_id, second_capture.attribution_id]
    assert rows[0].transfer_expires_at < datetime.now(UTC)
    assert rows[0].capture_idempotency_key_hash is None
    assert rows[1].capture_idempotency_key_hash == idempotency_hash
    assert "pat=" not in rows[0].destination_url
    assert "pat=" not in rows[1].destination_url


@pytest.mark.asyncio
async def test_capture_blocks_new_session_when_browser_has_five_active_pending_sessions(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    seed = await _seed_capture_fixture(pg_sessionmaker)
    now = datetime.now(UTC)
    browser_key = f"pg-active-limit-browser-key-{uuid.uuid4()}"
    browser_key_hash = hash_partner_attribution_token(browser_key)

    async with pg_sessionmaker() as session:
        for index in range(5):
            code_value = f"PGACT{index}{uuid.uuid4().hex[:12]}".upper()
            public_slug = f"pg-active-limit-{index}-{uuid.uuid4().hex}"
            extra_code = PartnerCodeModel(
                id=uuid.uuid4(),
                code=code_value,
                code_normalized=code_value,
                public_slug=public_slug,
                public_token_hash=hash_partner_attribution_token(public_slug),
                partner_account_id=seed.account_id,
                partner_user_id=seed.owner_id,
                markup_pct=7,
                is_active=True,
                lifecycle_status="active",
                approval_status="approved",
                owner_type="affiliate",
                lane_key="creator_affiliate",
                attribution_model="last_eligible_touch",
                attribution_window_seconds=30 * 24 * 60 * 60,
                allowed_channels=["content"],
                allowed_storefront_ids=["*"],
                allowed_geographies=["*"],
                sub_id_schema={},
            )
            session.add(extra_code)
            await session.flush()
            session.add(
                PartnerAttributionSessionModel(
                    session_token_hash=None,
                    transfer_token_hash=hash_partner_attribution_token(f"pg-active-transfer-{index}-{uuid.uuid4()}"),
                    transfer_expires_at=now + timedelta(minutes=15),
                    partner_code_id=extra_code.id,
                    partner_account_id=seed.account_id,
                    auth_realm_id=seed.realm.id,
                    status="pending",
                    owner_type="affiliate",
                    attribution_model="last_eligible_touch",
                    commission_contract_id=extra_code.commission_contract_id,
                    source_host="cyber-vpn.net",
                    source_path=f"/p/pg-active-{index}",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    browser_key_hash=browser_key_hash,
                    capture_idempotency_key_hash=hash_partner_attribution_token(
                        f"pg-active-idempotency-{index}-{uuid.uuid4()}"
                    ),
                    destination_url="https://my.cyber-vpn.net/ru-RU/pricing",
                    campaign_params={},
                    evidence_payload={},
                    policy_snapshot={},
                    expires_at=now + timedelta(days=30),
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
        await session.commit()

    async with pg_sessionmaker() as session:
        with pytest.raises(PartnerAttributionError) as exc_info:
            await CapturePartnerAttributionUseCase(session).execute(
                CapturePartnerAttributionCommand(
                    public_token=seed.public_slug,
                    source_host="cyber-vpn.net",
                    source_path="/p/pg-active-limit",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={"creator": "pg"},
                    click_id="pg-click",
                    browser_key=browser_key,
                    capture_idempotency_key="pg-active-limit-new-idempotency",
                    campaign_params={"utm_source": "pg"},
                    current_realm=RealmResolution(auth_realm=seed.realm, source="test"),
                )
            )

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "PARTNER_BROWSER_ACTIVE_SESSION_LIMIT"


@pytest.mark.asyncio
async def test_capture_active_session_limit_ignores_transfer_expired_pending_sessions(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "partner_legacy_code_public_slug_enabled", True)
    seed = await _seed_capture_fixture(pg_sessionmaker)
    now = datetime.now(UTC)
    browser_key = f"pg-expired-active-limit-browser-key-{uuid.uuid4()}"
    browser_key_hash = hash_partner_attribution_token(browser_key)

    async with pg_sessionmaker() as session:
        for index in range(5):
            session.add(
                PartnerAttributionSessionModel(
                    session_token_hash=None,
                    transfer_token_hash=hash_partner_attribution_token(f"pg-expired-transfer-{index}-{uuid.uuid4()}"),
                    transfer_expires_at=now - timedelta(minutes=1),
                    partner_code_id=seed.code_id,
                    partner_account_id=seed.account_id,
                    auth_realm_id=seed.realm.id,
                    status="pending",
                    owner_type="affiliate",
                    attribution_model="last_eligible_touch",
                    source_host="cyber-vpn.net",
                    source_path=f"/p/pg-expired-active-{index}",
                    destination_path="/pricing",
                    locale="ru-RU",
                    sale_channel="content",
                    sub_ids={},
                    browser_key_hash=browser_key_hash,
                    capture_idempotency_key_hash=hash_partner_attribution_token(
                        f"pg-expired-active-idempotency-{index}-{uuid.uuid4()}"
                    ),
                    destination_url="https://my.cyber-vpn.net/ru-RU/pricing",
                    campaign_params={},
                    evidence_payload={},
                    policy_snapshot={},
                    expires_at=now + timedelta(days=30),
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
        await session.commit()

    async with pg_sessionmaker() as session:
        capture = await CapturePartnerAttributionUseCase(session).execute(
            CapturePartnerAttributionCommand(
                public_token=seed.public_slug,
                source_host="cyber-vpn.net",
                source_path="/p/pg-expired-active-limit",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                sub_ids={"creator": "pg"},
                click_id="pg-click",
                browser_key=browser_key,
                capture_idempotency_key=f"pg-expired-active-limit-new-idempotency-{uuid.uuid4()}",
                campaign_params={"utm_source": "pg"},
                current_realm=RealmResolution(auth_realm=seed.realm, source="test"),
            )
        )
        await session.commit()

    assert capture.transfer_token
    async with pg_sessionmaker() as session:
        active_count = await session.scalar(
            select(func.count())
            .select_from(PartnerAttributionSessionModel)
            .where(
                PartnerAttributionSessionModel.partner_code_id == seed.code_id,
                PartnerAttributionSessionModel.browser_key_hash == browser_key_hash,
                PartnerAttributionSessionModel.transfer_expires_at > datetime.now(UTC),
                PartnerAttributionSessionModel.transfer_consumed_at.is_(None),
                PartnerAttributionSessionModel.status == "pending",
            )
        )
    assert active_count == 1


async def _cleanup_claim_fixture(maker: async_sessionmaker[AsyncSession], seed: _ClaimSeed) -> None:
    aggregate_ids = [str(item) for item in seed.session_ids]
    async with maker() as session:
        event_ids = (
            (await session.execute(select(OutboxEventModel.id).where(OutboxEventModel.aggregate_id.in_(aggregate_ids))))
            .scalars()
            .all()
        )
        if event_ids:
            await session.execute(
                delete(OutboxPublicationModel).where(OutboxPublicationModel.outbox_event_id.in_(event_ids))
            )
            await session.execute(delete(OutboxEventModel).where(OutboxEventModel.id.in_(event_ids)))
        await session.execute(
            delete(AttributionTouchpointModel).where(
                AttributionTouchpointModel.partner_attribution_session_id.in_(seed.session_ids)
            )
        )
        await session.execute(
            delete(CustomerCommercialBindingModel).where(CustomerCommercialBindingModel.user_id == seed.customer_id)
        )
        await session.execute(
            delete(PartnerAttributionSessionModel).where(PartnerAttributionSessionModel.id.in_(seed.session_ids))
        )
        await session.execute(delete(PartnerCodeModel).where(PartnerCodeModel.id.in_(seed.code_ids)))
        await session.execute(delete(PartnerAccountModel).where(PartnerAccountModel.id.in_(seed.account_ids)))
        await session.execute(
            delete(MobileUserModel).where(MobileUserModel.id.in_([seed.customer_id, *seed.owner_ids]))
        )
        await session.execute(delete(StorefrontModel).where(StorefrontModel.id.in_(seed.storefront_ids)))
        await session.execute(delete(BrandModel).where(BrandModel.id == seed.brand_id))
        await session.execute(delete(AuthRealmModel).where(AuthRealmModel.id == seed.realm.id))
        await session.commit()


async def _claim_cookie(
    maker: async_sessionmaker[AsyncSession],
    *,
    seed: _ClaimSeed,
    cookie_token: str,
) -> ClaimPartnerAttributionResult:
    async with maker() as session:
        try:
            result = await ClaimPartnerAttributionUseCase(session).execute(
                ClaimPartnerAttributionCommand(
                    user_id=seed.customer_id,
                    cookie_token=cookie_token,
                    current_realm=RealmResolution(auth_realm=seed.realm, source="test"),
                )
            )
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def _active_bindings_for_seed(
    maker: async_sessionmaker[AsyncSession],
    seed: _ClaimSeed,
) -> list[CustomerCommercialBindingModel]:
    async with maker() as session:
        result = await session.execute(
            select(CustomerCommercialBindingModel).where(
                CustomerCommercialBindingModel.user_id == seed.customer_id,
                CustomerCommercialBindingModel.binding_status == CustomerCommercialBindingStatus.ACTIVE.value,
            )
        )
        return list(result.scalars().all())


async def _set_session_storefront(
    maker: async_sessionmaker[AsyncSession],
    *,
    session_id: uuid.UUID,
    storefront_id: uuid.UUID,
) -> None:
    async with maker() as session:
        attribution = await session.get(PartnerAttributionSessionModel, session_id)
        assert attribution is not None
        attribution.storefront_id = storefront_id
        await session.commit()


def _binding(
    *,
    seed: _ClaimSeed,
    account_id: uuid.UUID | None,
    code_id: uuid.UUID | None,
    storefront_id: uuid.UUID | None = None,
    binding_type: str = CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
    owner_type: str = "affiliate",
    reason_code: str = "postgres_test_binding",
) -> CustomerCommercialBindingModel:
    return CustomerCommercialBindingModel(
        user_id=seed.customer_id,
        auth_realm_id=seed.realm.id,
        storefront_id=storefront_id,
        binding_type=binding_type,
        binding_status=CustomerCommercialBindingStatus.ACTIVE.value,
        owner_type=owner_type,
        partner_account_id=account_id,
        partner_code_id=code_id,
        reason_code=reason_code,
        evidence_payload={"source": "postgres_claim_test"},
        effective_from=datetime.now(UTC),
    )


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
    for index_name in _ACTIVE_OWNER_INDEXES:
        if index_name in details:
            return index_name
    return None


@pytest.mark.asyncio
async def test_postgres_same_owner_concurrent_claims_share_one_active_binding(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=True)
    try:
        results = await asyncio.gather(
            *[_claim_cookie(pg_sessionmaker, seed=seed, cookie_token=token) for token in seed.cookie_tokens]
        )

        assert sorted(result.status for result in results) == ["already_claimed_same_owner", "claimed"]
        assert len({result.binding_id for result in results}) == 1
        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        assert len(active_bindings) == 1
        assert active_bindings[0].partner_code_id == seed.code_ids[0]
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_different_owner_concurrent_claims_reject_second_owner(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False)
    try:
        results = await asyncio.gather(
            *[_claim_cookie(pg_sessionmaker, seed=seed, cookie_token=token) for token in seed.cookie_tokens]
        )

        assert sorted(result.status for result in results) == ["claimed", "rejected_existing_owner"]
        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        assert len(active_bindings) == 1
        assert active_bindings[0].partner_code_id in seed.code_ids

        async with pg_sessionmaker() as session:
            rejected_sessions = (
                (
                    await session.execute(
                        select(PartnerAttributionSessionModel).where(
                            PartnerAttributionSessionModel.id.in_(seed.session_ids),
                            PartnerAttributionSessionModel.status == "rejected",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(rejected_sessions) == 1
            assert rejected_sessions[0].rejection_reason_code == "existing_active_owner_conflict"
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_active_owner_partial_unique_index_blocks_duplicate_global_owner(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=1)
    try:
        async with pg_sessionmaker() as session:
            session.add(
                _binding(
                    seed=seed,
                    account_id=seed.account_ids[0],
                    code_id=seed.code_ids[0],
                    storefront_id=None,
                    binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                    reason_code="postgres_unique_index_first_owner",
                )
            )
            await session.commit()

        async with pg_sessionmaker() as session:
            session.add(
                _binding(
                    seed=seed,
                    account_id=seed.account_ids[0],
                    code_id=seed.code_ids[0],
                    storefront_id=None,
                    binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                    reason_code="postgres_unique_index_second_owner",
                )
            )
            with pytest.raises(IntegrityError) as exc_info:
                await session.commit()
            await session.rollback()
            assert _constraint_name(exc_info.value) == "uq_customer_commercial_bindings_active_owner_global_scope"

        async with pg_sessionmaker() as session:
            count = await session.scalar(
                select(func.count(CustomerCommercialBindingModel.id)).where(
                    CustomerCommercialBindingModel.user_id == seed.customer_id,
                    CustomerCommercialBindingModel.binding_status == CustomerCommercialBindingStatus.ACTIVE.value,
                )
            )
            assert count == 1
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_active_owner_partial_unique_index_allows_two_storefronts_but_blocks_duplicate_storefront(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=1)
    try:
        async with pg_sessionmaker() as session:
            session.add_all(
                [
                    _binding(
                        seed=seed,
                        account_id=seed.account_ids[0],
                        code_id=seed.code_ids[0],
                        storefront_id=seed.storefront_ids[0],
                        binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                        reason_code="postgres_unique_storefront_a",
                    ),
                    _binding(
                        seed=seed,
                        account_id=seed.account_ids[0],
                        code_id=seed.code_ids[0],
                        storefront_id=seed.storefront_ids[1],
                        binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                        reason_code="postgres_unique_storefront_b",
                    ),
                ]
            )
            await session.commit()

        async with pg_sessionmaker() as session:
            session.add(
                _binding(
                    seed=seed,
                    account_id=seed.account_ids[0],
                    code_id=seed.code_ids[0],
                    storefront_id=seed.storefront_ids[0],
                    binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                    reason_code="postgres_unique_storefront_duplicate",
                )
            )
            with pytest.raises(IntegrityError) as exc_info:
                await session.commit()
            await session.rollback()
            assert _constraint_name(exc_info.value) == "uq_customer_commercial_bindings_active_owner_storefront_scope"

        async with pg_sessionmaker() as session:
            count = await session.scalar(
                select(func.count(CustomerCommercialBindingModel.id)).where(
                    CustomerCommercialBindingModel.user_id == seed.customer_id,
                    CustomerCommercialBindingModel.binding_status == CustomerCommercialBindingStatus.ACTIVE.value,
                )
            )
            assert count == 2
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_storefront_claim_prefers_exact_storefront_owner_over_newer_global_immutable(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=2)
    await _set_session_storefront(
        pg_sessionmaker,
        session_id=seed.session_ids[0],
        storefront_id=seed.storefront_ids[0],
    )
    try:
        now = datetime.now(UTC)
        async with pg_sessionmaker() as session:
            exact_storefront = _binding(
                seed=seed,
                account_id=seed.account_ids[0],
                code_id=seed.code_ids[0],
                storefront_id=seed.storefront_ids[0],
                binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                reason_code="postgres_storefront_exact_owner",
            )
            exact_storefront.effective_from = now - timedelta(minutes=5)
            newer_global_manual = _binding(
                seed=seed,
                account_id=seed.account_ids[1],
                code_id=seed.code_ids[1],
                storefront_id=None,
                binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                reason_code="postgres_storefront_newer_global_manual",
            )
            newer_global_manual.effective_from = now + timedelta(minutes=5)
            session.add_all([exact_storefront, newer_global_manual])
            await session.commit()
            exact_storefront_id = exact_storefront.id

        result = await _claim_cookie(pg_sessionmaker, seed=seed, cookie_token=seed.cookie_tokens[0])

        assert result.status == "already_claimed_same_owner"
        assert result.binding_id == exact_storefront_id
        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        assert len(active_bindings) == 2

        async with pg_sessionmaker() as session:
            attribution = await session.get(PartnerAttributionSessionModel, seed.session_ids[0])
            assert attribution is not None
            assert attribution.status == "claimed"
            assert attribution.binding_id == exact_storefront_id
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_storefront_claim_treats_same_owner_global_immutable_as_already_claimed(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=1)
    await _set_session_storefront(
        pg_sessionmaker,
        session_id=seed.session_ids[0],
        storefront_id=seed.storefront_ids[0],
    )
    try:
        async with pg_sessionmaker() as session:
            global_manual = _binding(
                seed=seed,
                account_id=seed.account_ids[0],
                code_id=seed.code_ids[0],
                storefront_id=None,
                binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                reason_code="postgres_same_owner_global_manual",
            )
            session.add(global_manual)
            await session.commit()
            global_manual_id = global_manual.id

        result = await _claim_cookie(pg_sessionmaker, seed=seed, cookie_token=seed.cookie_tokens[0])

        assert result.status == "already_claimed_same_owner"
        assert result.binding_id == global_manual_id
        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        assert len(active_bindings) == 1

        async with pg_sessionmaker() as session:
            attribution = await session.get(PartnerAttributionSessionModel, seed.session_ids[0])
            assert attribution is not None
            assert attribution.status == "claimed"
            assert attribution.binding_id == global_manual_id
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("foreign_binding_type", "reason_code"),
    [
        (CustomerCommercialBindingType.MANUAL_OVERRIDE.value, "postgres_foreign_realm_global_manual"),
        (CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value, "postgres_foreign_realm_partner_attribution"),
    ],
)
async def test_postgres_claim_ignores_foreign_realm_active_owner(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
    foreign_binding_type: str,
    reason_code: str,
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=1)
    foreign_realm = AuthRealmModel(
        id=uuid.uuid4(),
        realm_key=f"pg-claim-foreign-{uuid.uuid4().hex}",
        realm_type="customer",
        display_name="PG Claim Foreign Realm",
        audience=f"cybervpn:pg-claim-foreign:{uuid.uuid4().hex}",
        cookie_namespace=f"pgforeign{uuid.uuid4().hex[:16]}",
        status="active",
        is_default=False,
    )
    try:
        async with pg_sessionmaker() as session:
            foreign_binding = _binding(
                seed=seed,
                account_id=seed.account_ids[0],
                code_id=seed.code_ids[0],
                storefront_id=None,
                binding_type=foreign_binding_type,
                reason_code=reason_code,
            )
            foreign_binding.auth_realm_id = foreign_realm.id
            session.add(foreign_realm)
            session.add(foreign_binding)
            await session.commit()
            foreign_binding_id = foreign_binding.id

        result = await _claim_cookie(pg_sessionmaker, seed=seed, cookie_token=seed.cookie_tokens[0])

        assert result.status == "claimed"
        assert result.binding_id is not None
        assert result.binding_id != foreign_binding_id

        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        active_by_id = {binding.id: binding for binding in active_bindings}
        assert set(active_by_id) == {foreign_binding_id, result.binding_id}
        assert active_by_id[foreign_binding_id].auth_realm_id == foreign_realm.id
        assert active_by_id[foreign_binding_id].binding_status == CustomerCommercialBindingStatus.ACTIVE.value
        assert active_by_id[result.binding_id].auth_realm_id == seed.realm.id

        async with pg_sessionmaker() as session:
            attribution = await session.get(PartnerAttributionSessionModel, seed.session_ids[0])
            assert attribution is not None
            assert attribution.status == "claimed"
            assert attribution.binding_id == result.binding_id
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)
        async with pg_sessionmaker() as session:
            await session.execute(delete(AuthRealmModel).where(AuthRealmModel.id == foreign_realm.id))
            await session.commit()


@pytest.mark.asyncio
async def test_postgres_future_global_owner_does_not_block_current_claim_without_current_owner(
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=2)
    try:
        async with pg_sessionmaker() as session:
            future_global_manual = _binding(
                seed=seed,
                account_id=seed.account_ids[1],
                code_id=seed.code_ids[1],
                storefront_id=None,
                binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                owner_type="performance",
                reason_code="postgres_future_global_manual_owner",
            )
            future_global_manual.effective_from = datetime.now(UTC) + timedelta(days=1)
            session.add(future_global_manual)
            await session.commit()
            future_binding_id = future_global_manual.id

        result = await _claim_cookie(pg_sessionmaker, seed=seed, cookie_token=seed.cookie_tokens[0])

        assert result.status == "claimed"
        assert result.binding_id is not None
        assert result.binding_id != future_binding_id
        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        assert {binding.id for binding in active_bindings} == {future_binding_id, result.binding_id}
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_claim_unique_conflict_maps_to_existing_owner_result(
    monkeypatch: pytest.MonkeyPatch,
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=1)
    original_list_active = CustomerCommercialBindingRepository.list_active_for_user
    calls = 0

    async def stale_preflight_once(
        self: CustomerCommercialBindingRepository,
        *,
        user_id: uuid.UUID,
        storefront_id: uuid.UUID | None,
        auth_realm_id: uuid.UUID | None = None,
        active_at: datetime | None = None,
        for_update: bool = False,
    ) -> list[CustomerCommercialBindingModel]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return []
        return await original_list_active(
            self,
            user_id=user_id,
            storefront_id=storefront_id,
            auth_realm_id=auth_realm_id,
            active_at=active_at,
            for_update=for_update,
        )

    monkeypatch.setattr(CustomerCommercialBindingRepository, "list_active_for_user", stale_preflight_once)

    try:
        async with pg_sessionmaker() as session:
            session.add(
                _binding(
                    seed=seed,
                    account_id=seed.account_ids[0],
                    code_id=seed.code_ids[0],
                    storefront_id=None,
                    binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                    reason_code="postgres_unique_conflict_existing_owner",
                )
            )
            await session.commit()

        result = await _claim_cookie(pg_sessionmaker, seed=seed, cookie_token=seed.cookie_tokens[0])

        assert result.status == "already_claimed_same_owner"
        assert result.binding_id is not None
        assert calls >= 2

        active_bindings = await _active_bindings_for_seed(pg_sessionmaker, seed)
        assert len(active_bindings) == 1
        assert active_bindings[0].id == result.binding_id

        async with pg_sessionmaker() as session:
            attribution = await session.get(PartnerAttributionSessionModel, seed.session_ids[0])
            assert attribution is not None
            assert attribution.status == "claimed"
            assert attribution.binding_id == result.binding_id
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_claim_unique_conflict_rolls_back_to_manual_review_without_duplicate_active_binding(
    monkeypatch: pytest.MonkeyPatch,
    pg_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    seed = await _seed_claim_fixture(pg_sessionmaker, same_owner=False, session_count=1)
    original_list_active = CustomerCommercialBindingRepository.list_active_for_user
    calls = 0

    async def stale_preflight_once(
        self: CustomerCommercialBindingRepository,
        *,
        user_id: uuid.UUID,
        storefront_id: uuid.UUID | None,
        auth_realm_id: uuid.UUID | None = None,
        active_at: datetime | None = None,
        for_update: bool = False,
    ) -> list[CustomerCommercialBindingModel]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return []
        return await original_list_active(
            self,
            user_id=user_id,
            storefront_id=storefront_id,
            auth_realm_id=auth_realm_id,
            active_at=active_at,
            for_update=for_update,
        )

    monkeypatch.setattr(CustomerCommercialBindingRepository, "list_active_for_user", stale_preflight_once)

    try:
        async with pg_sessionmaker() as session:
            session.add(
                _binding(
                    seed=seed,
                    account_id=None,
                    code_id=None,
                    storefront_id=None,
                    binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                    owner_type="direct_store",
                    reason_code="postgres_direct_store_conflict",
                )
            )
            await session.commit()

        result = await _claim_cookie(pg_sessionmaker, seed=seed, cookie_token=seed.cookie_tokens[0])

        assert result.status == "manual_review_required"
        assert result.binding_id is not None
        assert calls >= 2

        async with pg_sessionmaker() as session:
            active_bindings = (
                (
                    await session.execute(
                        select(CustomerCommercialBindingModel).where(
                            CustomerCommercialBindingModel.user_id == seed.customer_id,
                            CustomerCommercialBindingModel.binding_status
                            == CustomerCommercialBindingStatus.ACTIVE.value,
                        )
                    )
                )
                .scalars()
                .all()
            )
            attribution = await session.get(PartnerAttributionSessionModel, seed.session_ids[0])

        assert len(active_bindings) == 1
        assert active_bindings[0].owner_type == "direct_store"
        assert active_bindings[0].id == result.binding_id
        assert attribution is not None
        assert attribution.status == "rejected"
        assert attribution.rejection_reason_code == "manual_review_required_active_owner_conflict"
        assert attribution.binding_id is None
        assert attribution.claimed_at is None
    finally:
        await _cleanup_claim_fixture(pg_sessionmaker, seed)


@pytest.mark.asyncio
async def test_postgres_migration_preflight_blocks_duplicate_active_owner_data() -> None:
    database_name = f"cybervpn_claim_preflight_{uuid.uuid4().hex}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", PREVIOUS_REVISION)
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            await _insert_duplicate_active_owner_rows(engine)
        finally:
            await engine.dispose()

        result = await asyncio.to_thread(_run_alembic, url, "upgrade", HARDENING_REVISION, False)
        assert result.returncode != 0
        assert "duplicate active owners exist" in result.stderr
    finally:
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_postgres_migration_downgrade_and_reupgrade_restore_active_owner_indexes() -> None:
    database_name = f"cybervpn_claim_reupgrade_{uuid.uuid4().hex}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        await asyncio.to_thread(_run_alembic, url, "downgrade", PREVIOUS_REVISION)
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")

        engine = create_async_engine(url, pool_pre_ping=True)
        sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            seed = await _seed_claim_fixture(sessionmaker, same_owner=False, session_count=1)
            try:
                async with sessionmaker() as session:
                    session.add(
                        _binding(
                            seed=seed,
                            account_id=seed.account_ids[0],
                            code_id=seed.code_ids[0],
                            storefront_id=None,
                            binding_type=CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
                            reason_code="postgres_reupgrade_first_owner",
                        )
                    )
                    await session.commit()

                async with sessionmaker() as session:
                    session.add(
                        _binding(
                            seed=seed,
                            account_id=seed.account_ids[0],
                            code_id=seed.code_ids[0],
                            storefront_id=None,
                            binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                            reason_code="postgres_reupgrade_second_owner",
                        )
                    )
                    with pytest.raises(IntegrityError) as exc_info:
                        await session.commit()
                    await session.rollback()
                    assert (
                        _constraint_name(exc_info.value) == "uq_customer_commercial_bindings_active_owner_global_scope"
                    )
            finally:
                await _cleanup_claim_fixture(sessionmaker, seed)
        finally:
            await engine.dispose()
    finally:
        await _drop_database(database_name)


async def _insert_duplicate_active_owner_rows(engine) -> None:
    realm_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    owner_a_id = uuid.uuid4()
    owner_b_id = uuid.uuid4()
    account_a_id = uuid.uuid4()
    account_b_id = uuid.uuid4()
    code_a_id = uuid.uuid4()
    code_b_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                insert into auth_realms (
                    id, realm_key, realm_type, display_name, audience, cookie_namespace,
                    status, is_default, created_at, updated_at
                )
                values (
                    :realm_id, :realm_key, 'customer', 'Preflight Realm', :audience, :cookie_namespace,
                    'active', false, :now, :now
                )
                """
            ),
            {
                "realm_id": realm_id,
                "realm_key": f"preflight-{realm_id.hex[:16]}",
                "audience": f"cybervpn:preflight:{realm_id.hex}",
                "cookie_namespace": f"preflight{realm_id.hex[:16]}",
                "now": now,
            },
        )
        await conn.execute(
            text(
                """
                insert into mobile_users (
                    id, public_uid, auth_realm_id, email, password_hash, notification_prefs,
                    totp_enabled, is_partner, is_active, status, created_at, updated_at
                )
                values
                    (
                        :customer_id, 91000001, :realm_id, :customer_email,
                        'hash', '{}'::json, false, false, true, 'active', :now, :now
                    ),
                    (
                        :owner_a_id, 91000002, :realm_id, :owner_a_email,
                        'hash', '{}'::json, false, false, true, 'active', :now, :now
                    ),
                    (
                        :owner_b_id, 91000003, :realm_id, :owner_b_email,
                        'hash', '{}'::json, false, false, true, 'active', :now, :now
                    )
                """
            ),
            {
                "customer_id": customer_id,
                "owner_a_id": owner_a_id,
                "owner_b_id": owner_b_id,
                "realm_id": realm_id,
                "customer_email": f"preflight-customer-{realm_id.hex}@example.test",
                "owner_a_email": f"preflight-owner-a-{realm_id.hex}@example.test",
                "owner_b_email": f"preflight-owner-b-{realm_id.hex}@example.test",
                "now": now,
            },
        )
        await conn.execute(
            text(
                """
                insert into partner_accounts (
                    id, account_key, display_name, status, legacy_owner_user_id, created_at, updated_at
                )
                values
                    (:account_a_id, :account_a_key, 'Preflight Account A', 'active', :owner_a_id, :now, :now),
                    (:account_b_id, :account_b_key, 'Preflight Account B', 'active', :owner_b_id, :now, :now)
                """
            ),
            {
                "account_a_id": account_a_id,
                "account_b_id": account_b_id,
                "account_a_key": f"preflight-a-{realm_id.hex[:16]}",
                "account_b_key": f"preflight-b-{realm_id.hex[:16]}",
                "owner_a_id": owner_a_id,
                "owner_b_id": owner_b_id,
                "now": now,
            },
        )
        await conn.execute(
            text(
                """
                insert into partner_codes (
                    id, code, code_normalized, public_token_hash, partner_account_id, partner_user_id,
                    code_kind, lifecycle_status, owner_type, lane_key, attribution_model,
                    attribution_window_seconds, allowed_channels, allowed_storefront_ids,
                    allowed_geographies, sub_id_schema, approval_status, markup_pct, is_active,
                    version, created_at, updated_at
                )
                values
                    (
                        :code_a_id, :code_a, :code_a, :code_a_hash, :account_a_id, :owner_a_id,
                        'starter_code', 'active', 'affiliate', 'creator_affiliate', 'last_eligible_touch',
                        2592000, '["content"]'::json, '["*"]'::json, '["*"]'::json, '{}'::json,
                        'approved', 7, true, 1, :now, :now
                    ),
                    (
                        :code_b_id, :code_b, :code_b, :code_b_hash, :account_b_id, :owner_b_id,
                        'starter_code', 'active', 'affiliate', 'creator_affiliate', 'last_eligible_touch',
                        2592000, '["content"]'::json, '["*"]'::json, '["*"]'::json, '{}'::json,
                        'approved', 7, true, 1, :now, :now
                    )
                """
            ),
            {
                "code_a_id": code_a_id,
                "code_b_id": code_b_id,
                "code_a": f"PREFLIGHTA{realm_id.hex[:12]}".upper(),
                "code_b": f"PREFLIGHTB{realm_id.hex[:12]}".upper(),
                "code_a_hash": hash_partner_attribution_token(f"preflight-a-{realm_id.hex}"),
                "code_b_hash": hash_partner_attribution_token(f"preflight-b-{realm_id.hex}"),
                "account_a_id": account_a_id,
                "account_b_id": account_b_id,
                "owner_a_id": owner_a_id,
                "owner_b_id": owner_b_id,
                "now": now,
            },
        )
        await conn.execute(
            text(
                """
                insert into customer_commercial_bindings (
                    id, user_id, auth_realm_id, storefront_id, binding_type, binding_status,
                    owner_type, partner_account_id, partner_code_id, reason_code, evidence_payload,
                    effective_from, version, created_at, updated_at
                )
                values
                    (
                        :binding_a_id, :customer_id, :realm_id, null, 'partner_attribution', 'active',
                        'affiliate', :account_a_id, :code_a_id, 'preflight_duplicate_a', '{}'::json,
                        :now, 1, :now, :now
                    ),
                    (
                        :binding_b_id, :customer_id, :realm_id, null, 'manual_override', 'active',
                        'affiliate', :account_b_id, :code_b_id, 'preflight_duplicate_b', '{}'::json,
                        :now, 1, :now, :now
                    )
                """
            ),
            {
                "binding_a_id": uuid.uuid4(),
                "binding_b_id": uuid.uuid4(),
                "customer_id": customer_id,
                "realm_id": realm_id,
                "account_a_id": account_a_id,
                "account_b_id": account_b_id,
                "code_a_id": code_a_id,
                "code_b_id": code_b_id,
                "now": now,
            },
        )


def _database_url(database_name: str) -> str:
    test_url = _test_postgres_url()
    return make_url(test_url).set(database=database_name).render_as_string(hide_password=False)


def _asyncpg_admin_url() -> str:
    return _test_postgres_url().replace("postgresql+asyncpg://", "postgresql://", 1)


def _test_postgres_url() -> str:
    url = os.getenv("CYBERVPN_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("CYBERVPN_TEST_POSTGRES_URL is required for PostgreSQL claim migration tests")
    return url


async def _create_database(database_name: str) -> None:
    try:
        conn = await asyncpg.connect(_asyncpg_admin_url())
    except OSError as exc:
        pytest.skip(f"PostgreSQL is unavailable for partner attribution claim tests: {exc}")
    try:
        await conn.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await conn.close()


async def _drop_database(database_name: str) -> None:
    conn = await asyncpg.connect(_asyncpg_admin_url())
    try:
        await conn.execute(
            """
            select pg_terminate_backend(pid)
            from pg_stat_activity
            where datname = $1
              and pid <> pg_backend_pid()
            """,
            database_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        await conn.close()


def _run_alembic(url: str, command: str, revision: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", command, revision],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"alembic {command} {revision} failed with exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result
