"""Shared admin audit helpers for privileged Stage 1 actions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.shared.logging.sanitization import REDACTED, sanitize_email, sanitize_username

STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS = frozenset(
    {
        "admin_invite_created",
        "admin_invite_revoked",
        "customer_profile_updated",
        "customer_staff_note_created",
        "customer_vpn_enabled",
        "customer_vpn_disabled",
        "customer_vpn_credentials_regenerated",
        "customer_device_revoked",
        "customer_devices_revoked_all",
        "customer_password_reset",
        "customer_subscription_manual_granted",
        "customer_subscription_resynced",
        "customer_operations.verify_payout_account",
        "customer_operations.suspend_payout_account",
        "customer_operations.approve_payout_instruction",
        "customer_operations.reject_payout_instruction",
        "system_config.miniapp_runtime.updated",
        "system_config.miniapp_launch_readiness.updated",
        "system_config.miniapp_launch_action.executed",
        "commercial.pricebook.updated",
        "commercial.pricebook.published",
        "commercial.pricebook.scheduled",
        "commercial.pricebook.rolled_back",
        "commercial.context_options.updated",
        "admin.bootstrap.first_admin_created",
    }
)

_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "subscription_url",
    "config",
    "link",
    "short_uuid",
)


def build_admin_audit_details(details: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if details is None:
        return None
    return {str(key): _sanitize_admin_audit_value(str(key), value) for key, value in details.items()}


async def write_required_admin_audit_entry(
    *,
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | UUID | None,
    actor: AdminUserModel,
    request: Request,
    details: Mapping[str, Any] | None = None,
    old_value: Mapping[str, Any] | None = None,
) -> AuditLog:
    audit_entry = AuditLog(
        admin_id=actor.id,
        action=action,
        entity_type=resource_type,
        entity_id=str(resource_id) if resource_id is not None else None,
        old_value=build_admin_audit_details(old_value),
        new_value=build_admin_audit_details(details),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry


def _sanitize_admin_audit_value(key: str, value: Any) -> Any:
    lowered_key = key.lower()
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(child_key): _sanitize_admin_audit_value(str(child_key), child_value)
            for child_key, child_value in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [_sanitize_admin_audit_value(key, item) for item in value]
    if any(part in lowered_key for part in _SENSITIVE_KEY_PARTS):
        return REDACTED
    if "email" in lowered_key and isinstance(value, str):
        return sanitize_email(value)
    if any(part in lowered_key for part in ("username", "login")) and isinstance(value, str):
        return sanitize_username(value)
    if isinstance(value, str) and "://" in value:
        return REDACTED
    return value
