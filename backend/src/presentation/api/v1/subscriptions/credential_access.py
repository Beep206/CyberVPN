"""Fail-closed authorization boundary for customer VPN credential reads."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_remnawave_ref,
)
from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.subscriptions.generate_config import GenerateConfigUseCase
from src.config.settings import settings
from src.domain.enums import AdminRole, PrincipalClass
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies.auth import CurrentPrincipalActor
from src.presentation.dependencies.passkey_fresh_auth import enforce_passkey_fresh_auth

REMNAWAVE_IDENTITY_CONFLICT_DETAIL = "Customer VPN identity is not exactly reconciled"


async def resolve_exact_mobile_user_ref(
    db: AsyncSession,
    *,
    customer_id: UUID,
    expected_auth_realm_id: UUID | None,
) -> tuple[MobileUserModel, RemnawaveUserRef]:
    """Resolve one local customer to its exact, reconciled numeric upstream identity."""

    customer = await MobileUserRepository(db).get_by_id(customer_id)
    if customer is None or (expected_auth_realm_id is not None and customer.auth_realm_id != expected_auth_realm_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    try:
        user_ref = await resolve_exact_mapped_remnawave_ref(
            db,
            subject_type="mobile_user",
            subject_id=customer.id,
            numeric_user_id=customer.remnawave_user_id,
            legacy_uuid_raw=customer.remnawave_uuid,
        )
    except RemnawaveIdentityAccessConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=REMNAWAVE_IDENTITY_CONFLICT_DETAIL,
        ) from exc
    if user_ref is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=REMNAWAVE_IDENTITY_CONFLICT_DETAIL)
    return customer, user_ref


def require_customer_principal(
    actor: CurrentPrincipalActor,
    current_realm: RealmResolution,
) -> None:
    """Require an exact customer principal/realm binding."""

    if (
        current_realm.realm_type != "customer"
        or actor.principal_type != PrincipalClass.CUSTOMER.value
        or actor.auth_realm_id != current_realm.auth_realm.id
        or actor.auth_realm_key != current_realm.realm_key
        or actor.audience != current_realm.audience
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer realm required")


async def require_sensitive_config_admin(
    db: AsyncSession,
    *,
    actor: CurrentPrincipalActor,
    current_realm: RealmResolution,
) -> AdminUserModel:
    """Require a trusted admin with the dedicated live-credential permission."""

    if (
        current_realm.realm_type != "admin"
        or actor.principal_type != PrincipalClass.ADMIN.value
        or actor.auth_realm_id != current_realm.auth_realm.id
        or actor.auth_realm_key != current_realm.realm_key
        or actor.audience != current_realm.audience
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin realm required")

    admin = await AdminUserRepository(db).get_by_id(actor.principal_id)
    if (
        admin is None
        or not admin.is_active
        or admin.deleted_at is not None
        or admin.auth_realm_id != actor.auth_realm_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="VPN credential access denied")
    try:
        role = AdminRole(admin.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="VPN credential access denied") from exc
    if not has_permission(role, Permission.VPN_CREDENTIAL_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="VPN credential access denied")
    if settings.admin_2fa_required and not admin.totp_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin 2FA required")
    return admin


async def read_customer_vpn_credentials_as_admin(
    *,
    customer_id: UUID,
    request: Request,
    actor: CurrentPrincipalActor,
    current_realm: RealmResolution,
    db: AsyncSession,
    client: RemnawaveClient,
    redis_client: redis.Redis,
) -> dict[str, Any]:
    """Read live VPN credentials only after permission, fresh auth, and required audit."""

    admin = await require_sensitive_config_admin(db, actor=actor, current_realm=current_realm)
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(admin.id),
        principal_class=PrincipalClass.ADMIN.value,
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=f"subscription_config:read:{customer_id}",
    )
    customer, user_ref = await resolve_exact_mobile_user_ref(
        db,
        customer_id=customer_id,
        expected_auth_realm_id=None,
    )
    config = await GenerateConfigUseCase(client).execute(user_ref)
    await write_required_admin_audit_entry(
        db=db,
        action="customer_vpn_credentials_read",
        resource_type="mobile_user",
        resource_id=customer.id,
        actor=admin,
        request=request,
        details={
            "access_mode": "fresh_passkey",
            "identity_kind": "remnawave_numeric",
            "target_auth_realm_id": customer.auth_realm_id,
        },
    )
    await db.commit()
    return config
