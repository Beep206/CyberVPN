"""Pytest configuration and fixtures for testing."""

import asyncio
import hashlib
import importlib.util
import os
import secrets
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from asyncpg.exceptions import PostgresError
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.exc import SQLAlchemyError


def _non_secret_test_value(label: str, length: int = 64) -> str:
    return hashlib.sha512(f"pytest-local-placeholder-{label}".encode()).hexdigest()[:length]


TEST_ENV_DEFAULTS = {
    "ENVIRONMENT": "test",
    "REMNAWAVE_TOKEN": _non_secret_test_value("remnawave"),
    "JWT_SECRET": _non_secret_test_value("jwt"),
    "CRYPTOBOT_TOKEN": _non_secret_test_value("cryptobot"),
    "CORS_ORIGINS": "http://localhost:3000",
    "ENABLE_METRICS": "true",
    "CYBERVPN_DEVICE_COOKIE_PEPPER": _non_secret_test_value("device-cookie"),
    "TOTP_ENCRYPTION_KEY": _non_secret_test_value("totp"),
    "OAUTH_TOKEN_ENCRYPTION_KEY": _non_secret_test_value("oauth"),
}

for env_key, env_value in TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(env_key, env_value)

from src.config.settings import settings  # noqa: E402
from src.main import app  # noqa: E402

TEST_DB_AVAILABLE_ENV = "PYTEST_DOCKER_DB_AVAILABLE"
GLOBAL_POOL_CLEANUP_TEST_DIRS = frozenset({"e2e", "integration", "load", "security"})


def pytest_ignore_collect(collection_path, path=None, config=None) -> bool:  # noqa: ARG001
    """Skip Locust scenarios from normal pytest collection when Locust is absent."""
    if collection_path.name not in {"test_auth_load.py", "test_helix_load.py"}:
        return False

    return collection_path.parent.name == "load" and importlib.util.find_spec("locust") is None


@pytest.fixture(scope="session")
def test_settings():
    """Set up test environment variables."""
    # Store original values
    original_env = {}
    original_partner_flags = {
        "partner_portal_enabled": settings.partner_portal_enabled,
        "partner_codes_enabled": settings.partner_codes_enabled,
        "partner_attribution_enabled": settings.partner_attribution_enabled,
        "partner_reporting_enabled": settings.partner_reporting_enabled,
    }

    # Test environment variables
    test_env = {
        "ENVIRONMENT": os.environ.get("ENVIRONMENT", "test"),
        # Reuse the local Docker stack so integration tests hit the same
        # services as the application instead of an absent ad-hoc test DB.
        "DATABASE_URL": os.environ.get("DATABASE_URL", settings.database_url),
        "REDIS_URL": os.environ.get("REDIS_URL", settings.redis_url),
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "CORS_ORIGINS": "http://localhost:3000",
        "DEBUG": "true",
        "ENABLE_METRICS": "true",  # Enable Prometheus metrics for observability tests
    }

    # Set test environment variables
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    settings.partner_portal_enabled = True
    settings.partner_codes_enabled = True
    settings.partner_attribution_enabled = True
    settings.partner_reporting_enabled = True

    yield test_env

    for attr, value in original_partner_flags.items():
        setattr(settings, attr, value)

    # Restore original environment variables
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest_asyncio.fixture
async def async_client(test_settings) -> AsyncGenerator[AsyncClient]:
    """
    Create an async HTTP client for testing the FastAPI application.

    Yields:
        AsyncClient: HTTPX async client with ASGI transport
    """
    client_host = f"pytest-client-{uuid.uuid4().hex[:31]}"
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(client_host, 123)),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def ensure_repo_schema(test_settings) -> None:
    """Create repo-managed tables missing from the legacy Docker database.

    The local Docker stack ships an older Remnawave schema. Our backend adds
    extra auth/admin tables on top, so integration tests need a one-time
    metadata sync to make sure those tables exist before the suite runs.
    """
    if os.environ.get("SKIP_TEST_DB_BOOTSTRAP") == "1":
        os.environ.pop(TEST_DB_AVAILABLE_ENV, None)
        return

    from sqlalchemy.ext.asyncio import create_async_engine

    import src.infrastructure.database.models  # noqa: F401
    from src.infrastructure.database.session import Base

    schema_engine = create_async_engine(
        os.environ.get("DATABASE_URL", settings.database_url),
        echo=False,
        pool_pre_ping=True,
    )

    async def _sync_schema() -> None:
        try:
            async with schema_engine.begin() as conn:
                existing_tables = set(
                    (await conn.execute(text("select tablename from pg_tables where schemaname = 'public'")))
                    .scalars()
                    .all()
                )

                missing_tables_exist = any(table_name not in existing_tables for table_name in Base.metadata.tables)
                if missing_tables_exist:
                    await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))

                admin_users_exists = "admin_users" in existing_tables
                if admin_users_exists:
                    admin_user_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'admin_users'
                                    """
                                )
                            )
                        ).all()
                    }
                    if "auth_realm_id" not in admin_user_columns:
                        await conn.execute(text("alter table admin_users add column auth_realm_id uuid"))
                        await conn.execute(
                            text(
                                """
                                create index if not exists ix_admin_users_auth_realm_id
                                on admin_users (auth_realm_id)
                                """
                            )
                        )

                    totp_secret_length = await conn.scalar(
                        text(
                            """
                            select character_maximum_length
                            from information_schema.columns
                            where table_schema = 'public'
                              and table_name = 'admin_users'
                              and column_name = 'totp_secret'
                            """
                        )
                    )
                    if totp_secret_length is not None and int(totp_secret_length) < 255:
                        await conn.execute(text("alter table admin_users alter column totp_secret type varchar(255)"))

                mobile_users_exists = "mobile_users" in existing_tables
                if mobile_users_exists:
                    mobile_user_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'mobile_users'
                                    """
                                )
                            )
                        ).all()
                    }
                    if "auth_realm_id" not in mobile_user_columns:
                        await conn.execute(text("alter table mobile_users add column auth_realm_id uuid"))
                        await conn.execute(
                            text(
                                """
                                create index if not exists ix_mobile_users_auth_realm_id
                                on mobile_users (auth_realm_id)
                                """
                            )
                        )
                    if "public_uid" not in mobile_user_columns:
                        await conn.execute(text("alter table mobile_users add column public_uid bigint"))
                    await conn.execute(
                        text(
                            """
                            with numbered as (
                                select id, row_number() over (order by created_at, id) as rn
                                from mobile_users
                                where public_uid is null
                            )
                            update mobile_users
                            set public_uid = 10000000 + ((numbered.rn * 7919 + 31415926) % 90000000)
                            from numbered
                            where mobile_users.id = numbered.id
                            """
                        )
                    )
                    await conn.execute(text("alter table mobile_users alter column public_uid set not null"))
                    await conn.execute(
                        text(
                            """
                            create unique index if not exists ix_mobile_users_public_uid
                            on mobile_users (public_uid)
                            """
                        )
                    )
                    if "telegram_subject" not in mobile_user_columns:
                        await conn.execute(text("alter table mobile_users add column telegram_subject varchar(255)"))
                        await conn.execute(
                            text(
                                """
                                create unique index if not exists ix_mobile_users_telegram_subject
                                on mobile_users (telegram_subject)
                                """
                            )
                        )
                    if "notification_prefs" not in mobile_user_columns:
                        await conn.execute(
                            text(
                                "alter table mobile_users "
                                "add column notification_prefs json not null default '{}'::json"
                            )
                        )
                    if "partner_account_id" not in mobile_user_columns:
                        await conn.execute(text("alter table mobile_users add column partner_account_id uuid"))
                        await conn.execute(
                            text(
                                """
                                create index if not exists ix_mobile_users_partner_account_id
                                on mobile_users (partner_account_id)
                                """
                            )
                        )
                    if "trial_activated_at" not in mobile_user_columns:
                        await conn.execute(
                            text("alter table mobile_users add column trial_activated_at timestamp with time zone")
                        )
                    if "trial_expires_at" not in mobile_user_columns:
                        await conn.execute(
                            text("alter table mobile_users add column trial_expires_at timestamp with time zone")
                        )
                    if "totp_secret" not in mobile_user_columns:
                        await conn.execute(text("alter table mobile_users add column totp_secret varchar(255)"))
                    if "totp_enabled" not in mobile_user_columns:
                        await conn.execute(
                            text("alter table mobile_users add column totp_enabled boolean not null default false")
                        )

                refresh_tokens_exists = "refresh_tokens" in existing_tables
                if refresh_tokens_exists:
                    refresh_token_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'refresh_tokens'
                                    """
                                )
                            )
                        ).all()
                    }
                    await conn.execute(
                        text(
                            "alter table refresh_tokens drop constraint if exists fk_refresh_tokens_user_id_admin_users"
                        )
                    )
                    if "auth_realm_id" not in refresh_token_columns:
                        await conn.execute(text("alter table refresh_tokens add column auth_realm_id uuid"))
                    if "principal_class" not in refresh_token_columns:
                        await conn.execute(text("alter table refresh_tokens add column principal_class varchar(32)"))
                    if "principal_subject" not in refresh_token_columns:
                        await conn.execute(text("alter table refresh_tokens add column principal_subject varchar(255)"))
                    if "audience" not in refresh_token_columns:
                        await conn.execute(text("alter table refresh_tokens add column audience varchar(120)"))
                    if "scope_family" not in refresh_token_columns:
                        await conn.execute(text("alter table refresh_tokens add column scope_family varchar(50)"))

                    await conn.execute(
                        text(
                            """
                            insert into auth_realms (
                                id,
                                realm_key,
                                realm_type,
                                display_name,
                                audience,
                                cookie_namespace,
                                status,
                                is_default,
                                created_at,
                                updated_at
                            )
                            values (
                                '2acd89fc-8e1d-5e93-9aa9-04e60428001a',
                                'admin',
                                'admin',
                                'Admin Realm',
                                'cybervpn:admin',
                                'admin',
                                'active',
                                true,
                                now(),
                                now()
                            )
                            on conflict (realm_key) do nothing
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            update refresh_tokens rt
                            set
                                auth_realm_id = coalesce(ar.id, default_ar.id),
                                principal_class = coalesce(rt.principal_class, 'admin'),
                                principal_subject = coalesce(rt.principal_subject, rt.user_id::text),
                                audience = coalesce(rt.audience, ar.audience, default_ar.audience),
                                scope_family = coalesce(rt.scope_family, ar.realm_type, default_ar.realm_type)
                            from admin_users au
                            join auth_realms default_ar
                              on default_ar.realm_key = 'admin'
                            left join auth_realms ar
                              on ar.id = au.auth_realm_id
                            where rt.user_id = au.id
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            update refresh_tokens rt
                            set
                                auth_realm_id = coalesce(rt.auth_realm_id, ar.id),
                                principal_class = coalesce(rt.principal_class, 'admin'),
                                principal_subject = coalesce(rt.principal_subject, rt.user_id::text),
                                audience = coalesce(rt.audience, ar.audience),
                                scope_family = coalesce(rt.scope_family, ar.realm_type)
                            from auth_realms ar
                            where ar.realm_key = 'admin'
                              and (
                                rt.auth_realm_id is null
                                or rt.principal_class is null
                                or rt.principal_subject is null
                                or rt.audience is null
                                or rt.scope_family is null
                              )
                            """
                        )
                    )
                    await conn.execute(text("alter table refresh_tokens alter column auth_realm_id set not null"))
                    await conn.execute(text("alter table refresh_tokens alter column principal_class set not null"))
                    await conn.execute(text("alter table refresh_tokens alter column principal_subject set not null"))
                    await conn.execute(text("alter table refresh_tokens alter column audience set not null"))
                    await conn.execute(text("alter table refresh_tokens alter column scope_family set not null"))
                    await conn.execute(
                        text(
                            "create index if not exists ix_refresh_tokens_auth_realm_id "
                            "on refresh_tokens (auth_realm_id)"
                        )
                    )
                    await conn.execute(
                        text(
                            "create index if not exists ix_refresh_tokens_principal_class "
                            "on refresh_tokens (principal_class)"
                        )
                    )
                    await conn.execute(
                        text(
                            "create index if not exists ix_refresh_tokens_principal_subject "
                            "on refresh_tokens (principal_subject)"
                        )
                    )
                    await conn.execute(
                        text("create index if not exists ix_refresh_tokens_audience on refresh_tokens (audience)")
                    )
                    await conn.execute(
                        text(
                            "create index if not exists ix_refresh_tokens_scope_family on refresh_tokens (scope_family)"
                        )
                    )
                    await conn.execute(
                        text(
                            "create index if not exists ix_refresh_tokens_principal_owner "
                            "on refresh_tokens (principal_class, principal_subject, auth_realm_id)"
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            do $$
                            begin
                                if not exists (
                                    select 1
                                    from pg_constraint
                                    where conname = 'ck_refresh_tokens_principal_class'
                                ) then
                                    alter table refresh_tokens
                                    add constraint ck_refresh_tokens_principal_class
                                    check (principal_class in ('admin', 'partner_operator', 'customer'));
                                end if;
                                if not exists (
                                    select 1
                                    from pg_constraint
                                    where conname = 'ck_refresh_tokens_principal_subject_nonempty'
                                ) then
                                    alter table refresh_tokens
                                    add constraint ck_refresh_tokens_principal_subject_nonempty
                                    check (principal_subject <> '');
                                end if;
                                if not exists (
                                    select 1
                                    from pg_constraint
                                    where conname = 'ck_refresh_tokens_audience_nonempty'
                                ) then
                                    alter table refresh_tokens
                                    add constraint ck_refresh_tokens_audience_nonempty
                                    check (audience <> '');
                                end if;
                                if not exists (
                                    select 1
                                    from pg_constraint
                                    where conname = 'ck_refresh_tokens_scope_family_nonempty'
                                ) then
                                    alter table refresh_tokens
                                    add constraint ck_refresh_tokens_scope_family_nonempty
                                    check (scope_family <> '');
                                end if;
                                if not exists (
                                    select 1
                                    from pg_constraint
                                    where conname = 'fk_refresh_tokens_auth_realm_id'
                                ) then
                                    alter table refresh_tokens
                                    add constraint fk_refresh_tokens_auth_realm_id
                                    foreign key (auth_realm_id) references auth_realms(id) on delete cascade;
                                end if;
                            end $$;
                            """
                        )
                    )

                subscription_plans_exists = "subscription_plans" in existing_tables
                if subscription_plans_exists:
                    subscription_plan_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'subscription_plans'
                                    """
                                )
                            )
                        ).all()
                    }
                    if "plan_code" not in subscription_plan_columns:
                        await conn.execute(text("alter table subscription_plans add column plan_code varchar(20)"))
                        await conn.execute(
                            text(
                                """
                                create index if not exists ix_subscription_plans_plan_code
                                on subscription_plans (plan_code)
                                """
                            )
                        )
                    if "display_name" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column display_name varchar(100) not null default ''"
                            )
                        )
                    if "catalog_visibility" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans add column "
                                "catalog_visibility varchar(20) not null default 'hidden'"
                            )
                        )
                    if "sale_channels" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column sale_channels jsonb not null default '[]'::jsonb"
                            )
                        )
                    if "traffic_policy" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column traffic_policy jsonb not null default '{}'::jsonb"
                            )
                        )
                    if "connection_modes" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans add column "
                                "connection_modes jsonb not null default '[]'::jsonb"
                            )
                        )
                    if "server_pool" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column server_pool jsonb not null default '[]'::jsonb"
                            )
                        )
                    if "support_sla" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column support_sla varchar(20) not null default 'standard'"
                            )
                        )
                    if "dedicated_ip" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column dedicated_ip jsonb not null default '{}'::jsonb"
                            )
                        )
                    if "invite_bundle" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column invite_bundle jsonb not null default '{}'::jsonb"
                            )
                        )
                    if "trial_eligible" not in subscription_plan_columns:
                        await conn.execute(
                            text(
                                "alter table subscription_plans "
                                "add column trial_eligible boolean not null default false"
                            )
                        )

                payments_exists = "payments" in existing_tables
                if payments_exists:
                    payment_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'payments'
                                    """
                                )
                            )
                        ).all()
                    }
                    if "addons_snapshot" not in payment_columns:
                        await conn.execute(text("alter table payments add column addons_snapshot json"))
                    if "entitlements_snapshot" not in payment_columns:
                        await conn.execute(text("alter table payments add column entitlements_snapshot json"))

                partner_codes_exists = "partner_codes" in existing_tables
                if partner_codes_exists:
                    partner_code_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'partner_codes'
                                    """
                                )
                            )
                        ).all()
                    }
                    if "partner_account_id" not in partner_code_columns:
                        await conn.execute(text("alter table partner_codes add column partner_account_id uuid"))
                        await conn.execute(
                            text(
                                """
                                create index if not exists ix_partner_codes_partner_account_id
                                on partner_codes (partner_account_id)
                                """
                            )
                        )

                growth_code_issuances_exists = "growth_code_issuances" in existing_tables
                if growth_code_issuances_exists:
                    growth_code_issuance_columns = {
                        row[0]
                        for row in (
                            await conn.execute(
                                text(
                                    """
                                    select column_name
                                    from information_schema.columns
                                    where table_schema = 'public'
                                      and table_name = 'growth_code_issuances'
                                    """
                                )
                            )
                        ).all()
                    }
                    if "raw_code_encrypted" not in growth_code_issuance_columns:
                        await conn.execute(text("alter table growth_code_issuances add column raw_code_encrypted text"))
        finally:
            await schema_engine.dispose()

    try:
        asyncio.run(_sync_schema())
    except (OSError, PostgresError, SQLAlchemyError) as exc:
        os.environ[TEST_DB_AVAILABLE_ENV] = "0"
        print(f"pytest test DB bootstrap skipped: {exc}")
        return

    os.environ[TEST_DB_AVAILABLE_ENV] = "1"


@pytest_asyncio.fixture(autouse=True)
async def cleanup_global_async_pools(request) -> AsyncGenerator[None]:
    """Dispose shared pools after tests that exercise app-level async resources."""
    yield

    test_path = request.node.path
    try:
        relative_parts = test_path.relative_to(request.config.rootpath).parts
    except ValueError:
        relative_parts = test_path.parts
    test_dir = relative_parts[1] if len(relative_parts) > 1 and relative_parts[0] == "tests" else None
    if test_dir not in GLOBAL_POOL_CLEANUP_TEST_DIRS:
        return

    from src.infrastructure.cache.redis_client import close_redis_pool
    from src.infrastructure.database.session import engine
    from src.infrastructure.helix.client import helix_adapter_client
    from src.infrastructure.payments.cryptobot.client import cryptobot_client
    from src.infrastructure.remnawave.client import remnawave_client

    await remnawave_client.close()
    await helix_adapter_client.close()
    await cryptobot_client.close()
    await close_redis_pool()
    await engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator:
    """
    Create a test database session.

    Creates tables, yields session, then rolls back and cleans up.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    # Use the Docker-backed database configured for the local stack.
    test_db_url = os.environ.get("DATABASE_URL", settings.database_url)
    if os.environ.get(TEST_DB_AVAILABLE_ENV) == "0":
        pytest.skip(
            f"Docker-backed test database is unavailable for {test_db_url}. "
            "Start the local stack or run targeted sqlite-backed packs."
        )

    # Create test engine
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_tokens() -> AsyncGenerator[dict[str, str]]:
    """Create a live super-admin token for integration/e2e tests that need auth."""

    from src.application.services.auth_service import AuthService
    from src.infrastructure.database.models import AdminUserModel
    from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
    from src.infrastructure.database.session import AsyncSessionLocal

    auth_service = AuthService()
    user_id = uuid.uuid4()
    login_suffix = secrets.token_hex(4)
    password_hash = await auth_service.hash_password("FixtureAdminPassword123!")

    async with AsyncSessionLocal() as session:
        admin_realm = await AuthRealmRepository(session).get_or_create_default_realm("admin")
        user = AdminUserModel(
            id=user_id,
            auth_realm_id=admin_realm.id,
            login=f"pytest-admin-{login_suffix}",
            email=f"pytest-admin-{login_suffix}@example.com",
            password_hash=password_hash,
            role="super_admin",
            is_active=True,
            is_email_verified=True,
            language="en-EN",
            timezone="UTC",
        )
        session.add(user)
        await session.commit()

    access_token, _jti, _access_exp = auth_service.create_access_token(
        subject=str(user_id),
        role="super_admin",
        audience=admin_realm.audience,
        principal_type="admin",
        realm_id=str(admin_realm.id),
        realm_key=admin_realm.realm_key,
        scope_family=admin_realm.realm_type,
    )

    try:
        yield {"access_token": access_token}
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(AdminUserModel).where(AdminUserModel.id == user_id))
            await session.commit()


@pytest.fixture
def auth_headers(auth_tokens: dict[str, str]) -> dict[str, str]:
    """Authorization headers for tests that need an authenticated admin request."""

    return {
        "Authorization": f"Bearer {auth_tokens['access_token']}",
        "Host": "testserver",
        "X-Forwarded-Host": "admin.cyber-vpn.net",
    }
