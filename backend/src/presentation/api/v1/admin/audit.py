"""Shared admin audit helpers for privileged Stage 1 actions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.presentation.middleware.request_id import get_request_id
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
        "commercial_catalog.plan.created",
        "commercial_catalog.plan.updated",
        "commercial_catalog.plan.deleted",
        "commercial_catalog.addon.created",
        "commercial_catalog.addon.updated",
        "commercial_catalog.offer.created",
        "commercial_catalog.pricebook.created",
    }
)

_SENSITIVE_KEY_PARTS = (
    "api-key",
    "api_key",
    "apikey",
    "access-key",
    "access_key",
    "private-key",
    "private_key",
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


async def write_required_commercial_catalog_audit_entry(
    *,
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | UUID | None,
    actor: AdminUserModel,
    request: Request,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    source: str = "admin_api",
    reason: str | None = None,
) -> AuditLog:
    sanitized_before = build_admin_audit_details(before)
    sanitized_after = build_admin_audit_details(after)
    request_id = _audit_request_id(request)
    correlation_id = _audit_correlation_id(request) or request_id
    diff_hash = _audit_diff_hash(before=sanitized_before, after=sanitized_after)
    metadata = {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "diff_hash": diff_hash,
        "source": source,
    }
    if reason is not None:
        metadata["reason"] = reason

    return await write_required_admin_audit_entry(
        db=db,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        request=request,
        old_value={"before": sanitized_before, **metadata},
        details={"after": sanitized_after, **metadata},
    )


def _audit_diff_hash(
    *,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
) -> str:
    payload = json.dumps(
        {"before": before, "after": after},
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _audit_request_id(request: Request) -> str | None:
    return get_request_id() or _request_header(request, "x-request-id")


def _audit_correlation_id(request: Request) -> str | None:
    return _request_header(request, "x-correlation-id")


def _request_header(request: Request, header_name: str) -> str | None:
    headers = request.headers
    return (
        headers.get(header_name)
        or headers.get(header_name.upper())
        or headers.get("-".join(part.capitalize() for part in header_name.split("-")))
    )


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
