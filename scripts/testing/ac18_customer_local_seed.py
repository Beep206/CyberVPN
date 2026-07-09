"""Seed a local customer for AC-18 live BFF/browser smoke evidence.

The script is local-only. It refuses non-loopback database URLs and writes
generated credentials only under .private so live smoke evidence can stay
sanitized.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import socket
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.session import AsyncSessionLocal, engine

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_OUTPUT = REPO_ROOT / ".private" / "latest-customer-smoke.json"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
FORBIDDEN_HOSTS = {
    "45.87.41.146",
    "prod-app-1",
    "my.cyber-vpn.net",
    "api.cyber-vpn.net",
}
SMOKE_LOGIN = "ac18_customer_smoke"
SMOKE_EMAIL = "ac18-customer-smoke@example.invalid"


def _database_host(url: str) -> str:
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    return (parsed.hostname or "").lower()


def _is_loopback(host: str) -> bool:
    if host in LOCAL_HOSTS:
        return True
    try:
        return all(
            socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)[0][4][0].startswith(
                "127."
            )
            for _ in [host]
        )
    except socket.gaierror:
        return False


def _assert_local_database() -> None:
    host = _database_host(settings.database_url)
    if host in FORBIDDEN_HOSTS or not _is_loopback(host):
        raise RuntimeError(
            "Refusing to seed customer smoke data into a non-local database. "
            f"Resolved host: {host or '<missing>'}."
        )


def _new_password() -> str:
    return f"Ac18CustomerSmoke-{secrets.token_urlsafe(18)}_1!"


async def _get_or_create_realm(
    session,
    *,
    realm_key: str,
    realm_type: str,
    display_name: str,
) -> AuthRealmModel:
    result = await session.execute(
        select(AuthRealmModel).where(AuthRealmModel.realm_key == realm_key)
    )
    realm = result.scalar_one_or_none()
    if realm is not None:
        realm.realm_type = realm_type
        realm.display_name = display_name
        realm.audience = f"cybervpn:{realm_key}"
        realm.cookie_namespace = realm_key
        realm.status = "active"
        realm.is_default = True
        return realm

    realm = AuthRealmModel(
        realm_key=realm_key,
        realm_type=realm_type,
        display_name=display_name,
        audience=f"cybervpn:{realm_key}",
        cookie_namespace=realm_key,
        status="active",
        is_default=True,
    )
    session.add(realm)
    await session.flush()
    return realm


async def _get_or_create_web_customer(
    session,
    auth_service: AuthService,
    *,
    customer_realm: AuthRealmModel,
    password: str,
) -> AdminUserModel:
    result = await session.execute(
        select(AdminUserModel).where(
            AdminUserModel.auth_realm_id == customer_realm.id,
            AdminUserModel.login == SMOKE_LOGIN,
        )
    )
    customer = result.scalar_one_or_none()
    password_hash = await auth_service.hash_password(password)
    now = datetime.now(UTC)

    if customer is None:
        customer = AdminUserModel(
            login=SMOKE_LOGIN,
            email=SMOKE_EMAIL,
            auth_realm_id=customer_realm.id,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            status="active",
            language="ru",
            timezone="UTC",
            display_name="AC-18 Live Customer",
            notification_prefs={},
            tos_accepted_at=now,
        )
        session.add(customer)
        await session.flush()
        return customer

    customer.email = SMOKE_EMAIL
    customer.auth_realm_id = customer_realm.id
    customer.password_hash = password_hash
    customer.role = "viewer"
    customer.is_active = True
    customer.is_email_verified = True
    customer.status = "active"
    customer.language = "ru"
    customer.timezone = customer.timezone or "UTC"
    customer.display_name = customer.display_name or "AC-18 Live Customer"
    customer.notification_prefs = customer.notification_prefs or {}
    customer.tos_accepted_at = customer.tos_accepted_at or now
    await session.flush()
    return customer


async def _ensure_mobile_shadow(
    session,
    *,
    customer: AdminUserModel,
    customer_realm: AuthRealmModel,
    password_hash: str,
    subscription_url: str,
) -> MobileUserModel:
    result = await session.execute(
        select(MobileUserModel).where(MobileUserModel.id == customer.id)
    )
    mobile = result.scalar_one_or_none()
    if mobile is None:
        mobile = MobileUserModel(
            id=customer.id,
            auth_realm_id=customer_realm.id,
            email=SMOKE_EMAIL,
            password_hash=password_hash,
            username=SMOKE_LOGIN[:50],
            notification_prefs={},
            remnawave_uuid=None,
            subscription_url=subscription_url,
            referral_code=f"A18C{secrets.token_hex(4).upper()}"[:12],
            is_active=True,
            status="active",
        )
        session.add(mobile)
        await session.flush()
        return mobile

    mobile.auth_realm_id = customer_realm.id
    mobile.email = SMOKE_EMAIL
    mobile.password_hash = password_hash
    mobile.username = mobile.username or SMOKE_LOGIN[:50]
    mobile.notification_prefs = mobile.notification_prefs or {}
    mobile.remnawave_uuid = None
    mobile.subscription_url = subscription_url
    mobile.is_active = True
    mobile.status = "active"
    await session.flush()
    return mobile


async def main() -> None:
    _assert_local_database()
    auth_service = AuthService()
    password = _new_password()
    subscription_token = secrets.token_urlsafe(16)
    subscription_url = f"https://subscription.example.invalid/ac18/{subscription_token}"

    async with AsyncSessionLocal() as session:
        customer_realm = await _get_or_create_realm(
            session,
            realm_key="customer",
            realm_type="customer",
            display_name="Customer",
        )
        customer = await _get_or_create_web_customer(
            session,
            auth_service,
            customer_realm=customer_realm,
            password=password,
        )
        mobile = await _ensure_mobile_shadow(
            session,
            customer=customer,
            customer_realm=customer_realm,
            password_hash=customer.password_hash or "",
            subscription_url=subscription_url,
        )
        await session.commit()

    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "origin": "http://127.0.0.1:9464",
                "login": SMOKE_LOGIN,
                "email": SMOKE_EMAIL,
                "password": password,
                "user_id": str(customer.id),
                "mobile_user_id": str(mobile.id),
                "subscription_url_present": True,
                "subscription_url_host": "subscription.example.invalid",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
