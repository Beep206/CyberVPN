"""One-time first admin bootstrap for Stage 1.

This script intentionally creates no public route. It must be run from a
protected operator shell after clean migrations and with secrets supplied via
environment variables.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pyotp

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT_STR = str(BACKEND_ROOT)
if BACKEND_ROOT_STR in sys.path:
    sys.path.remove(BACKEND_ROOT_STR)
sys.path.insert(0, BACKEND_ROOT_STR)

BOOTSTRAP_CONFIRM_VALUE = "CREATE_FIRST_ADMIN"
BOOTSTRAP_AUDIT_ACTION = "admin.bootstrap.first_admin_created"
BOOTSTRAP_LOCK_KEY = "cybervpn:first_admin_bootstrap"


class BootstrapError(Exception):
    """Safe bootstrap failure that can be printed without leaking secrets."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class BootstrapConfig:
    confirm: str
    owner_handle: str
    login: str
    email: str
    password: str
    totp_secret: str
    totp_code: str
    source_ip: str

    def redacted(self) -> dict[str, str | bool]:
        return {
            "owner_handle": self.owner_handle,
            "login": self.login,
            "email": self.email,
            "password_supplied": bool(self.password),
            "totp_secret_supplied": bool(self.totp_secret),
            "totp_code_supplied": bool(self.totp_code),
            "source_ip": self.source_ip,
        }


def _required_env(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise BootstrapError("missing_env", f"{key} is required")
    return value


def _validate_password(password: str, login: str, email: str) -> None:
    lowered = password.lower()
    weak_fragments = {"password", "admin", "cybervpn", login.lower(), email.lower().split("@", maxsplit=1)[0]}
    if len(password) < 16:
        raise BootstrapError("weak_password", "bootstrap password must be at least 16 characters")
    if any(fragment and fragment in lowered for fragment in weak_fragments):
        raise BootstrapError("weak_password", "bootstrap password contains a weak or account-derived fragment")


def _validate_totp_secret(secret: str) -> None:
    try:
        base64.b32decode(secret.upper(), casefold=True)
    except Exception as exc:  # noqa: BLE001
        raise BootstrapError("invalid_totp_secret", "bootstrap TOTP secret must be valid base32") from exc


def load_config_from_env(env: Mapping[str, str] | None = None) -> BootstrapConfig:
    source = os.environ if env is None else env
    confirm = _required_env(source, "CYBERVPN_BOOTSTRAP_CONFIRM")
    if confirm != BOOTSTRAP_CONFIRM_VALUE:
        raise BootstrapError("confirmation_required", "CYBERVPN_BOOTSTRAP_CONFIRM must equal CREATE_FIRST_ADMIN")

    owner_handle = source.get("CYBERVPN_BOOTSTRAP_OWNER_HANDLE", "@Sasha_Beep").strip() or "@Sasha_Beep"
    login = _required_env(source, "CYBERVPN_BOOTSTRAP_LOGIN")
    email = _required_env(source, "CYBERVPN_BOOTSTRAP_EMAIL").lower()
    password = _required_env(source, "CYBERVPN_BOOTSTRAP_PASSWORD")
    totp_secret = _required_env(source, "CYBERVPN_BOOTSTRAP_TOTP_SECRET").replace(" ", "")
    totp_code = _required_env(source, "CYBERVPN_BOOTSTRAP_TOTP_CODE")
    source_ip = source.get("CYBERVPN_BOOTSTRAP_SOURCE_IP", "operator-shell").strip() or "operator-shell"

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", login):
        raise BootstrapError(
            "invalid_login", "bootstrap login must be 3-50 ASCII letters, digits, dot, underscore or dash"
        )
    if len(email) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise BootstrapError("invalid_email", "bootstrap email must be a valid email address")
    _validate_password(password, login, email)
    if not re.fullmatch(r"\d{6}", totp_code):
        raise BootstrapError("invalid_totp_code", "bootstrap TOTP code must be six digits")
    _validate_totp_secret(totp_secret)
    if len(source_ip) > 45:
        raise BootstrapError("invalid_source_ip", "bootstrap source IP/label must fit the audit ip_address field")

    return BootstrapConfig(
        confirm=confirm,
        owner_handle=owner_handle,
        login=login,
        email=email,
        password=password,
        totp_secret=totp_secret,
        totp_code=totp_code,
        source_ip=source_ip,
    )


def build_audit_payload(config: BootstrapConfig) -> dict[str, object]:
    return {
        "login": config.login,
        "email": config.email,
        "role": "owner/super_admin",
        "totp_enabled": True,
        "bootstrap_owner_handle": config.owner_handle,
        "bootstrap_method": "one_time_cli",
        "default_credentials": False,
        "permanent_public_endpoint": False,
        "secrets_redacted": True,
    }


async def bootstrap_first_admin(config: BootstrapConfig) -> dict[str, object]:
    from sqlalchemy import func, select, text

    from src.application.services.auth_service import AuthService
    from src.config.settings import settings
    from src.domain.enums import AdminRole
    from src.infrastructure.database.models.admin_user_model import AdminUserModel
    from src.infrastructure.database.models.audit_log_model import AuditLog
    from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
    from src.infrastructure.database.session import AsyncSessionLocal
    from src.infrastructure.totp.totp_service import TOTPService

    if settings.environment in {"staging", "production"} and not settings.totp_encryption_key.get_secret_value():
        raise BootstrapError(
            "totp_encryption_key_required", "TOTP_ENCRYPTION_KEY is required for staging/production bootstrap"
        )

    if not pyotp.TOTP(config.totp_secret).verify(config.totp_code, valid_window=1):
        raise BootstrapError("invalid_totp_code", "bootstrap TOTP code verification failed")

    totp = TOTPService()
    password_hash = await AuthService.hash_password(config.password)
    stored_totp_secret = totp.encrypt_secret(config.totp_secret)
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("select pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": BOOTSTRAP_LOCK_KEY}
            )

            admin_count = await session.scalar(select(func.count()).select_from(AdminUserModel))
            bootstrap_count = await session.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == BOOTSTRAP_AUDIT_ACTION)
            )
            if admin_count or bootstrap_count:
                raise BootstrapError(
                    "bootstrap_locked",
                    "first admin bootstrap is locked because admin or bootstrap audit state already exists",
                )

            admin_realm = await session.scalar(
                select(AuthRealmModel).where(
                    AuthRealmModel.realm_key == "admin",
                    AuthRealmModel.realm_type == "admin",
                    AuthRealmModel.status == "active",
                )
            )
            if admin_realm is None:
                raise BootstrapError(
                    "admin_realm_missing", "active admin auth realm is required before first admin bootstrap"
                )

            admin_user = AdminUserModel(
                login=config.login,
                email=config.email,
                auth_realm_id=admin_realm.id,
                password_hash=password_hash,
                role=AdminRole.OWNER_SUPER_ADMIN.value,
                is_active=True,
                totp_secret=stored_totp_secret,
                totp_enabled=True,
                status="active",
                is_email_verified=True,
                password_changed_at=now,
                display_name="CyberVPN Owner",
                language="en",
                timezone="UTC",
                notification_prefs={"bootstrap_owner_handle": config.owner_handle, "stage": "S1"},
            )
            session.add(admin_user)
            await session.flush()

            audit_log = AuditLog(
                admin_id=admin_user.id,
                action=BOOTSTRAP_AUDIT_ACTION,
                entity_type="admin_user",
                entity_id=str(admin_user.id),
                old_value=None,
                new_value=build_audit_payload(config),
                ip_address=config.source_ip,
                user_agent="S1-BE-002 first-admin bootstrap CLI",
            )
            session.add(audit_log)

            return {
                "status": "created",
                "admin_user_id": str(admin_user.id),
                "login": admin_user.login,
                "email": admin_user.email,
                "role": admin_user.role,
                "totp_enabled": admin_user.totp_enabled,
                "audit_action": BOOTSTRAP_AUDIT_ACTION,
                "auth_realm": admin_realm.realm_key,
            }


async def _async_main() -> int:
    try:
        config = load_config_from_env()
        result = await bootstrap_first_admin(config)
    except BootstrapError as exc:
        print(
            json.dumps({"status": "failed", "reason": exc.code, "message": exc.message}, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    except Exception:
        print(
            json.dumps({"status": "failed", "reason": "internal_error", "message": "bootstrap failed"}, sort_keys=True),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
