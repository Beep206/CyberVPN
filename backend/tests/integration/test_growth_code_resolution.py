from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.domain.enums import InviteSource
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeModel,
    GrowthCodeReservationModel,
    GrowthCodeResolutionEventModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_quote_checkout_sessions import _make_customer_access_token, _seed_quote_context

pytestmark = [pytest.mark.integration]


async def _create_admin_user(sessionmaker, auth_service: AuthService) -> tuple[AdminUserModel, str]:
    password = "AdminLookupPhase5!"
    with sessionmaker() as db:
        user = AdminUserModel(
            login="growthlookup",
            email="growth-lookup@example.test",
            password_hash=await auth_service.hash_password(password),
            role="admin",
            is_active=True,
            is_email_verified=True,
            language="en",
            timezone="UTC",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, password


@pytest.mark.asyncio
async def test_codes_resolve_returns_wrong_context_for_invite_in_checkout(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="invite-owner@example.test",
                    password_hash=await auth_service.hash_password("InviteOwner123!"),
                    is_active=True,
                    status="active",
                )
                invite = InviteCodeModel(
                    id=uuid.uuid4(),
                    code="INVITETEST01",
                    owner_user_id=owner.id,
                    free_days=14,
                    source=InviteSource.ADMIN_GRANT.value,
                    is_used=False,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
                db.add_all([owner, invite])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": invite.code,
                    "action_context": "checkout",
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is False
            assert payload["code_type"] == "invite"
            assert payload["result"] == "rejected"
            assert payload["reject_reason"] == "code_wrong_context"
            assert payload["wrong_context_target"] == "redeem"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_codes_resolve_accepts_promo_for_checkout(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMORESOLVE10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                db.add(promo)
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": promo.code,
                    "action_context": "checkout",
                    "plan_id": seeded["plan_id"],
                    "amount": 90,
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is True
            assert payload["code_type"] == "promo"
            assert payload["result"] == "accepted"
            assert payload["promo_code_id"] == str(promo.id)

            with sessionmaker() as db:
                shadow_code = db.execute(
                    select(GrowthCodeModel).where(
                        GrowthCodeModel.code_hash == hash_growth_code(promo.code),
                        GrowthCodeModel.code_type == "promo",
                    )
                ).scalar_one()
                resolution_events = db.execute(
                    select(GrowthCodeResolutionEventModel).where(
                        GrowthCodeResolutionEventModel.growth_code_id == shadow_code.id
                    )
                ).scalars().all()

                assert shadow_code.status == "active"
                assert shadow_code.issuer_type == "admin"
                assert len(resolution_events) == 1
                assert resolution_events[0].result == "accepted"
                assert resolution_events[0].surface == "web"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_growth_code_lookup_returns_operator_safe_resolution(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            await _create_admin_user(sessionmaker, auth_service)

            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="ADMINLOOKUP10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                db.add(promo)
                db.commit()

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": "growth-lookup@example.test",
                    "password": "AdminLookupPhase5!",
                },
            )
            assert login_response.status_code == 200
            access_token = login_response.json()["access_token"]

            response = await async_client.post(
                "/api/v1/admin/growth-codes/lookup",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "code": promo.code,
                    "action_context": "checkout",
                    "lookup_user_id": seeded["customer_user_id"],
                    "storefront_key": seeded["storefront_key"],
                    "plan_id": seeded["plan_id"],
                    "amount": 90,
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is True
            assert payload["code_type"] == "promo"
            assert payload["result"] == "accepted"
            assert payload["promo_code_id"] == str(promo.id)
            assert payload["user_message_key"] == "growth_codes.promo.accepted"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_codes_resolve_records_not_found_attempt_without_shadow_code(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": "NOTREALWB0201",
                    "action_context": "checkout",
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is False
            assert payload["code_type"] is None
            assert payload["result"] == "rejected"
            assert payload["reject_reason"] == "code_not_found"

            with sessionmaker() as db:
                shadow_codes = db.execute(
                    select(GrowthCodeModel).where(
                        GrowthCodeModel.code_hash == hash_growth_code("NOTREALWB0201")
                    )
                ).scalars().all()
                resolution_events = db.execute(
                    select(GrowthCodeResolutionEventModel).where(
                        GrowthCodeResolutionEventModel.raw_code_hash == hash_growth_code("NOTREALWB0201")
                    )
                ).scalars().all()

                assert shadow_codes == []
                assert len(resolution_events) == 1
                assert resolution_events[0].growth_code_id is None
                assert resolution_events[0].result == "rejected"
                assert resolution_events[0].reject_reason == "code_not_found"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_codes_resolve_conflicts_promo_with_active_partner_binding(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOBIND10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                binding = CustomerCommercialBindingModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=customer_realm.id,
                    binding_type="reseller_binding",
                    binding_status="active",
                    owner_type="reseller",
                    reason_code="test_partner_flow",
                    evidence_payload={"source": "test"},
                )
                db.add_all([promo, binding])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": promo.code,
                    "action_context": "checkout",
                    "plan_id": seeded["plan_id"],
                    "amount": 90,
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is False
            assert payload["code_type"] == "promo"
            assert payload["result"] == "conflicted"
            assert payload["reject_reason"] == "code_conflicts_with_partner_binding"
            assert payload["conflict_code"] == "partner_binding_present"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_codes_resolve_conflicts_promo_with_storefront_scoped_partner_binding(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOSTOREFRONT10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                binding = CustomerCommercialBindingModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    binding_type="reseller_binding",
                    binding_status="active",
                    owner_type="reseller",
                    reason_code="test_storefront_partner_flow",
                    evidence_payload={"source": "test"},
                )
                db.add_all([promo, binding])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/codes/resolve",
                headers=headers,
                json={
                    "code": promo.code,
                    "action_context": "checkout",
                    "storefront_key": seeded["storefront_key"],
                    "plan_id": seeded["plan_id"],
                    "amount": 90,
                    "channel": "web",
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["accepted"] is False
            assert payload["code_type"] == "promo"
            assert payload["result"] == "conflicted"
            assert payload["reject_reason"] == "code_conflicts_with_partner_binding"
            assert payload["conflict_code"] == "partner_binding_present"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_quote_rejects_promo_when_active_partner_binding_exists(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                promo = PromoCodeModel(
                    id=uuid.uuid4(),
                    code="PROMOQUOTE10",
                    discount_type="percent",
                    discount_value=10,
                    is_active=True,
                )
                binding = CustomerCommercialBindingModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=customer_realm.id,
                    binding_type="reseller_binding",
                    binding_status="active",
                    owner_type="reseller",
                    reason_code="test_partner_flow",
                    evidence_payload={"source": "test"},
                )
                db.add_all([promo, binding])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "promo_code": promo.code,
                    "use_wallet": 0,
                    "addons": [],
                },
            )

            assert response.status_code == 400
            assert response.json()["detail"] == "Promo codes cannot be combined with active partner bindings"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_quote_derives_partner_markup_from_active_binding_code(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="partner-owner@example.test",
                    password_hash=await auth_service.hash_password("PartnerOwner123!"),
                    is_active=True,
                    status="active",
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="BINDMARK15",
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                binding = CustomerCommercialBindingModel(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=customer_realm.id,
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    binding_type="reseller_binding",
                    binding_status="active",
                    owner_type="reseller",
                    partner_code_id=partner_code.id,
                    reason_code="test_binding_markup",
                    evidence_payload={"source": "test"},
                )
                db.add_all([partner_owner, partner_code, binding])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "use_wallet": 0,
                    "addons": [],
                },
            )

            assert response.status_code == 201
            payload = response.json()
            assert payload["quote"]["partner_code_id"] == str(partner_code.id)
            assert payload["quote"]["partner_markup"] == 13.5
            assert payload["quote"]["displayed_price"] == 103.5
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_quote_accepts_referral_code_without_creating_reservation(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                referral_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="referral-owner@example.test",
                    referral_code="REFERQUOTE10",
                    password_hash=await auth_service.hash_password("ReferralOwner123!"),
                    is_active=True,
                    status="active",
                )
                db.add(referral_owner)
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            response = await async_client.post(
                "/api/v1/quotes/",
                headers=headers,
                json={
                    "storefront_key": seeded["storefront_key"],
                    "pricebook_key": seeded["pricebook_key"],
                    "offer_key": seeded["offer_key"],
                    "plan_id": seeded["plan_id"],
                    "currency": "USD",
                    "channel": "web",
                    "code_input": "REFERQUOTE10",
                    "use_wallet": 0,
                    "addons": [],
                },
            )

            assert response.status_code == 201
            payload = response.json()
            assert payload["quote"]["code_input"] == "REFERQUOTE10"
            assert payload["quote"]["code_resolution"]["code_type"] == "referral"
            assert payload["quote"]["code_resolution"]["result"] == "accepted"
            assert payload["quote"]["code_resolution"]["reservation_id"] is None
            assert payload["quote"]["discounts"] == [
                {
                    "type": "referral",
                    "code": "REFERQUOTE10",
                    "amount": 9.0,
                    "policy_version_id": None,
                }
            ]
            assert payload["quote"]["discount_amount"] == 9.0
            assert payload["quote"]["gateway_amount"] == 81.0

            with sessionmaker() as db:
                shadow_code = db.execute(
                    select(GrowthCodeModel).where(
                        GrowthCodeModel.code_hash == hash_growth_code("REFERQUOTE10"),
                        GrowthCodeModel.code_type == "referral",
                    )
                ).scalar_one()
                reservations = db.execute(
                    select(GrowthCodeReservationModel).where(
                        GrowthCodeReservationModel.growth_code_id == shadow_code.id
                    )
                ).scalars().all()

                assert reservations == []
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
