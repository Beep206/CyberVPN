from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.subscription_gateway.resolve import (
    ResolveSubscriptionProductUseCase,
    SubscriptionGatewayNotFoundError,
    SubscriptionGatewayUnavailableError,
)
from src.config.settings import settings
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.api.subscription_gateway import routes as subscription_gateway_routes
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.subscription_gateway import get_remnawave_subscription_proxy_client
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

PROVIDER_SUBJECT_REF = "e131349d-1d45-4a21-ac66-4e98fa54c22d"
SHORT_UUID = "abcdefghijklmnop"
ACTIVE_FROM = datetime(2020, 1, 1, tzinfo=UTC)
_DEFAULT_GRANT_SNAPSHOT = object()


class _RemnawaveClient:
    def __init__(self) -> None:
        self.paths: list[str] = []

    async def get(self, path: str) -> dict[str, object]:
        self.paths.append(path)
        return {
            "uuid": PROVIDER_SUBJECT_REF,
            "status": "ACTIVE",
            "externalSquadUuid": "409147a7-a03c-4db5-bccf-33d3caaf8d52",
        }


async def test_provider_subject_conflict_older_than_newest_three_fails_closed() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()
    base_created_at = datetime(2026, 1, 1, tzinfo=UTC)

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            newest_valid_smart = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=1,
                plan_code="premium_smart_ru",
                created_at=base_created_at + timedelta(minutes=3),
                grant_status="active",
            )
            _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=2,
                plan_code="unrelated_plan",
                created_at=base_created_at + timedelta(minutes=2),
                grant_status="active",
            )
            _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=3,
                plan_code="premium_smart_ru",
                created_at=base_created_at + timedelta(minutes=1),
                grant_status=None,
            )
            oldest_conflicting_spb = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=4,
                plan_code="premium_spb_de_exceptions",
                created_at=base_created_at,
                grant_status="active",
            )
            db.commit()

            client = _RemnawaveClient()
            use_case = ResolveSubscriptionProductUseCase(
                cast(AsyncSession, SyncSessionAdapter(db)),
                cast(RemnawaveClient, client),
            )

            with pytest.raises(SubscriptionGatewayUnavailableError):
                await use_case.execute(SHORT_UUID)

            assert client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert newest_valid_smart.provider_subject_ref == PROVIDER_SUBJECT_REF
            assert oldest_conflicting_spb.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


async def test_provider_active_with_expired_backend_grant_is_not_authorized() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            identity = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=1,
                plan_code="premium_smart_ru",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                grant_status="active",
                expires_at=datetime(2020, 1, 2, tzinfo=UTC),
            )
            db.commit()

            client = _RemnawaveClient()
            use_case = ResolveSubscriptionProductUseCase(
                cast(AsyncSession, SyncSessionAdapter(db)),
                cast(RemnawaveClient, client),
            )

            with pytest.raises(SubscriptionGatewayNotFoundError):
                await use_case.execute(SHORT_UUID)

            assert client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert identity.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


async def test_provider_subject_unsupported_conflict_older_than_newest_three_fails_closed() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()
    base_created_at = datetime(2026, 1, 1, tzinfo=UTC)

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            newest_valid_smart = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=11,
                plan_code="premium_smart_ru",
                created_at=base_created_at + timedelta(minutes=3),
                grant_status="active",
            )
            _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=12,
                plan_code="premium_smart_ru",
                created_at=base_created_at + timedelta(minutes=2),
                grant_status=None,
            )
            _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=13,
                plan_code="premium_smart_ru",
                created_at=base_created_at + timedelta(minutes=1),
                grant_status=None,
            )
            oldest_unsupported_conflict = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=14,
                plan_code="unrelated_plan",
                created_at=base_created_at,
                grant_status="active",
            )
            db.commit()

            client = _RemnawaveClient()
            use_case = ResolveSubscriptionProductUseCase(
                cast(AsyncSession, SyncSessionAdapter(db)),
                cast(RemnawaveClient, client),
            )

            with pytest.raises(SubscriptionGatewayUnavailableError):
                await use_case.execute(SHORT_UUID)

            assert client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert newest_valid_smart.provider_subject_ref == PROVIDER_SUBJECT_REF
            assert oldest_unsupported_conflict.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


async def test_provider_subject_grant_snapshot_mismatch_fails_closed() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            identity = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=21,
                plan_code="premium_spb_de_exceptions",
                grant_plan_code="premium_smart_ru",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                grant_status="active",
            )
            db.commit()

            client = _RemnawaveClient()
            use_case = ResolveSubscriptionProductUseCase(
                cast(AsyncSession, SyncSessionAdapter(db)),
                cast(RemnawaveClient, client),
            )

            with pytest.raises(SubscriptionGatewayUnavailableError):
                await use_case.execute(SHORT_UUID)

            assert client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert identity.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


async def test_public_gateway_returns_503_for_active_task2_grant_until_data_plane_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()

    class _FailIfProxied:
        async def fetch(self, short_uuid: str, *, headers: dict[str, str]):  # noqa: ARG002
            raise AssertionError("Task2 readiness false must not proxy subscription content")

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            identity = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=31,
                plan_code="premium_spb_de_exceptions",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                grant_status="active",
            )
            db.commit()

            management_client = _RemnawaveClient()
            app = FastAPI()
            app.include_router(subscription_gateway_routes.router)

            async def _db_override():
                yield cast(AsyncSession, SyncSessionAdapter(db))

            async def _management_override():
                return cast(RemnawaveClient, management_client)

            async def _proxy_override():
                return _FailIfProxied()

            app.dependency_overrides[get_db] = _db_override
            app.dependency_overrides[get_remnawave_client] = _management_override
            app.dependency_overrides[get_remnawave_subscription_proxy_client] = _proxy_override

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://cyber-vpn.org",
            ) as client:
                response = await client.get("/api/sub/abcdefghijklmnop", headers={"User-Agent": "INCY/1.2"})

            assert response.status_code == 503
            assert response.text == "Subscription service unavailable"
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["retry-after"] == "30"
            assert management_client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert identity.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


async def test_public_gateway_returns_503_for_active_task2_grant_when_attestation_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", "")
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()

    class _FailIfProxied:
        async def fetch(self, short_uuid: str, *, headers: dict[str, str]):  # noqa: ARG002
            raise AssertionError("Task2 missing readiness attestation must not proxy subscription content")

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            identity = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=33,
                plan_code="premium_spb_de_exceptions",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                grant_status="active",
            )
            db.commit()

            management_client = _RemnawaveClient()
            app = FastAPI()
            app.include_router(subscription_gateway_routes.router)

            async def _db_override():
                yield cast(AsyncSession, SyncSessionAdapter(db))

            async def _management_override():
                return cast(RemnawaveClient, management_client)

            async def _proxy_override():
                return _FailIfProxied()

            app.dependency_overrides[get_db] = _db_override
            app.dependency_overrides[get_remnawave_client] = _management_override
            app.dependency_overrides[get_remnawave_subscription_proxy_client] = _proxy_override

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://cyber-vpn.org",
            ) as client:
                response = await client.get("/api/sub/abcdefghijklmnop", headers={"User-Agent": "INCY/1.2"})

            assert response.status_code == 503
            assert response.text == "Subscription service unavailable"
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["retry-after"] == "30"
            assert management_client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert identity.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


async def test_public_gateway_returns_503_for_task2_identity_with_sparse_active_grant_until_data_plane_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    realm_id = uuid.uuid4()

    class _FailIfProxied:
        async def fetch(self, short_uuid: str, *, headers: dict[str, str]):  # noqa: ARG002
            raise AssertionError("Task2 readiness false must not proxy subscription content")

    try:
        with sessionmaker() as db:
            _insert_realm(db, realm_id)
            identity = _insert_identity_with_optional_grant(
                db,
                realm_id=realm_id,
                sequence=32,
                plan_code="premium_spb_de_exceptions",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                grant_status="active",
                grant_snapshot={},
            )
            db.commit()

            management_client = _RemnawaveClient()
            app = FastAPI()
            app.include_router(subscription_gateway_routes.router)

            async def _db_override():
                yield cast(AsyncSession, SyncSessionAdapter(db))

            async def _management_override():
                return cast(RemnawaveClient, management_client)

            async def _proxy_override():
                return _FailIfProxied()

            app.dependency_overrides[get_db] = _db_override
            app.dependency_overrides[get_remnawave_client] = _management_override
            app.dependency_overrides[get_remnawave_subscription_proxy_client] = _proxy_override

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="https://cyber-vpn.org",
            ) as client:
                response = await client.get("/api/sub/abcdefghijklmnop", headers={"User-Agent": "INCY/1.2"})

            assert response.status_code == 503
            assert response.text == "Subscription service unavailable"
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["retry-after"] == "30"
            assert management_client.paths == [f"/users/by-short-uuid/{SHORT_UUID}"]
            assert identity.provider_subject_ref == PROVIDER_SUBJECT_REF
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


def _insert_realm(db, realm_id: uuid.UUID) -> None:
    db.add(
        AuthRealmModel(
            id=realm_id,
            realm_key=f"subscription-gateway-{realm_id.hex[:8]}",
            realm_type="customer",
            display_name="Subscription Gateway Security",
            audience=f"subscription-gateway-{realm_id.hex[:8]}",
            cookie_namespace="customer",
            status="active",
            is_default=True,
        )
    )


def _insert_identity_with_optional_grant(
    db,
    *,
    realm_id: uuid.UUID,
    sequence: int,
    plan_code: str,
    created_at: datetime,
    grant_status: str | None,
    grant_plan_code: str | None = None,
    grant_snapshot: object = _DEFAULT_GRANT_SNAPSHOT,
    expires_at: datetime | None = None,
) -> ServiceIdentityModel:
    customer_id = uuid.uuid4()
    service_identity_id = uuid.uuid4()
    subscription_key = f"grant:{uuid.uuid4()}"
    db.add(
        MobileUserModel(
            id=customer_id,
            public_uid=930_000_000 + sequence,
            auth_realm_id=realm_id,
            email=f"subscription-gateway-security-{sequence}@example.test",
            password_hash="hashed",
        )
    )
    identity = ServiceIdentityModel(
        id=service_identity_id,
        service_key=f"svc_subscription_gateway_security_{sequence}",
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        provider_name="remnawave",
        identity_scope="subscription",
        subscription_key=subscription_key,
        provider_subject_ref=PROVIDER_SUBJECT_REF,
        identity_status="active",
        service_context={"plan_code": plan_code, "subscription_key": subscription_key},
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(identity)
    if grant_status is not None:
        resolved_grant_snapshot = (
            {"plan_code": grant_plan_code or plan_code} if grant_snapshot is _DEFAULT_GRANT_SNAPSHOT else grant_snapshot
        )
        assert isinstance(resolved_grant_snapshot, dict)
        db.add(
            EntitlementGrantModel(
                id=uuid.uuid4(),
                grant_key=f"subscription-gateway-security-grant-{sequence}",
                service_identity_id=service_identity_id,
                customer_account_id=customer_id,
                auth_realm_id=realm_id,
                source_type="manual",
                grant_status=grant_status,
                grant_snapshot=resolved_grant_snapshot,
                source_snapshot={"test": "subscription_gateway_security"},
                effective_from=ACTIVE_FROM,
                expires_at=expires_at,
                activated_at=ACTIVE_FROM,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    return identity
