"""Passkey/WebAuthn policy and compliance routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import redis.asyncio as redis
import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import (
    PASSKEY_ADMIN_POLICY_CONFIG_KEY,
    ConfigService,
    PasskeyAdminPolicyConfig,
)
from src.config.settings import settings
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import AdminRole, PrincipalClass
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_workspace_profile_model import PartnerWorkspaceProfileModel
from src.infrastructure.database.models.passkey_credential_model import PasskeyCredentialModel
from src.infrastructure.database.models.system_config_model import SystemConfigModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_workspace_profile_repository import (
    PartnerWorkspaceProfileRepository,
)
from src.infrastructure.database.repositories.passkey_credential_repo import PasskeyCredentialRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.api.v1.auth.passkey_schemas import (
    PartnerWorkspacePasskeyComplianceResponse,
    PartnerWorkspacePasskeyOperatorComplianceResponse,
    PartnerWorkspacePasskeyPolicyResponse,
    PasskeyComplianceCredentialResponse,
    PasskeyComplianceResponse,
    PasskeyComplianceSummaryResponse,
    PasskeyPolicyResponse,
    UpdateAdminPasskeyPolicyRequest,
    UpdatePartnerWorkspacePasskeyPolicyRequest,
)
from src.presentation.api.v1.auth.realm_context import get_principal_type_for_realm
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.auth_realms import get_request_admin_realm, get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    enforce_partner_workspace_permission,
    resolve_partner_workspace_access,
)
from src.presentation.dependencies.passkey_fresh_auth import enforce_passkey_fresh_auth
from src.presentation.dependencies.roles import require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["passkeys", "security"])

_STALE_CREDENTIAL_AFTER = timedelta(days=90)
_PASSKEY_ADMIN_POLICY_CONFIG_DESCRIPTION = "Operator-controlled admin passkey/WebAuthn runtime policy."


def _track(action: str, metric_status: str) -> None:
    route_operations_total.labels(route="auth.passkey_policy", action=action, status=metric_status).inc()
    sentry_sdk.add_breadcrumb(
        category="auth.passkeys",
        message=action,
        data={"status": metric_status},
        level="info",
    )


def _surface_feature_enabled(surface: str) -> bool:
    if surface == "admin":
        return settings.passkey_admin_enabled
    if surface == "partner":
        return settings.passkey_partner_enabled
    if surface == "customer":
        return settings.passkey_customer_enabled
    return False


def _surface_enabled(surface: str) -> bool:
    return settings.passkey_enabled and _surface_feature_enabled(surface)


def _allowed_origins() -> list[str]:
    origins = list(settings.passkey_allowed_origins)
    if settings.passkey_dev_enabled:
        origins.extend(origin for origin in settings.passkey_dev_allowed_origins if origin not in origins)
    return origins


def _admin_policy_payload(config: PasskeyAdminPolicyConfig) -> dict[str, object]:
    return {
        "enabled": config.enabled,
        "registration_enabled": config.registration_enabled,
        "authentication_enabled": config.authentication_enabled,
        "reauthentication_enabled": config.reauthentication_enabled,
        "conditional_ui_enabled": config.conditional_ui_enabled,
        "security_dashboard_enabled": config.security_dashboard_enabled,
        "admin_counts_as_mfa": config.admin_counts_as_mfa,
        "challenge_ttl_seconds": config.challenge_ttl_seconds,
        "browser_timeout_ms": config.browser_timeout_ms,
        "fresh_auth_ttl_seconds": config.fresh_auth_ttl_seconds,
    }


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _policy_response(
    *,
    surface: str,
    realm_key: str,
    admin_policy: PasskeyAdminPolicyConfig | None = None,
    config_model: SystemConfigModel | None = None,
) -> PasskeyPolicyResponse:
    global_enabled = settings.passkey_enabled
    surface_enabled = _surface_feature_enabled(surface)
    configured_enabled = admin_policy.enabled if admin_policy is not None else True
    enabled = global_enabled and surface_enabled and configured_enabled
    conditional_ui_enabled = True
    security_dashboard_enabled = settings.passkey_admin_security_dashboard_enabled if surface == "admin" else None
    admin_counts_as_mfa = settings.passkey_admin_counts_as_mfa
    challenge_ttl_seconds = settings.passkey_challenge_ttl_seconds
    browser_timeout_ms = settings.passkey_browser_timeout_ms
    fresh_auth_ttl_seconds = settings.passkey_fresh_auth_ttl_seconds

    if admin_policy is not None:
        conditional_ui_enabled = admin_policy.conditional_ui_enabled
        security_dashboard_enabled = admin_policy.security_dashboard_enabled
        admin_counts_as_mfa = admin_policy.admin_counts_as_mfa
        challenge_ttl_seconds = admin_policy.challenge_ttl_seconds
        browser_timeout_ms = admin_policy.browser_timeout_ms
        fresh_auth_ttl_seconds = admin_policy.fresh_auth_ttl_seconds

    return PasskeyPolicyResponse(
        enabled=enabled,
        configured_enabled=configured_enabled,
        global_enabled=global_enabled,
        surface_enabled=surface_enabled,
        surface=surface,
        realm_key=realm_key,
        rp_id=settings.passkey_rp_id,
        rp_name=settings.passkey_rp_name,
        allowed_origins=_allowed_origins(),
        conditional_ui_enabled=settings.passkey_conditional_ui_enabled and enabled and conditional_ui_enabled,
        registration_enabled=enabled and (admin_policy.registration_enabled if admin_policy is not None else True),
        authentication_enabled=enabled and (admin_policy.authentication_enabled if admin_policy is not None else True),
        reauthentication_enabled=(
            enabled and (admin_policy.reauthentication_enabled if admin_policy is not None else True)
        ),
        security_dashboard_enabled=(
            settings.passkey_admin_security_dashboard_enabled and enabled and bool(security_dashboard_enabled)
            if surface == "admin"
            else None
        ),
        workspace_policy_enabled=(
            settings.passkey_partner_workspace_policy_enabled if surface == "partner" else None
        ),
        admin_counts_as_mfa=admin_counts_as_mfa,
        challenge_ttl_seconds=challenge_ttl_seconds,
        browser_timeout_ms=browser_timeout_ms,
        fresh_auth_ttl_seconds=fresh_auth_ttl_seconds,
        policy_source="system_config" if config_model is not None else "settings",
        updated_at=config_model.updated_at if config_model is not None else None,
        updated_by=config_model.updated_by if config_model is not None else None,
    )


async def _get_admin_policy_state(
    db: AsyncSession,
) -> tuple[SystemConfigRepository, ConfigService, SystemConfigModel | None, PasskeyAdminPolicyConfig]:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    model = await repo.get_by_key(PASSKEY_ADMIN_POLICY_CONFIG_KEY)
    config = await service.get_passkey_admin_policy_config()
    return repo, service, model, config


async def _write_admin_policy_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    previous_payload: dict[str, object],
    next_payload: dict[str, object],
    change_reason: str | None,
) -> None:
    db.add(
        AuditLog(
            admin_id=actor.id,
            action="passkey.admin_policy.updated",
            entity_type="system_config",
            entity_id=PASSKEY_ADMIN_POLICY_CONFIG_KEY,
            old_value=previous_payload,
            new_value={**next_payload, "change_reason": change_reason},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    await db.flush()


async def _write_partner_policy_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    workspace_id: UUID,
    previous_payload: dict[str, object],
    next_payload: dict[str, object],
    change_reason: str | None,
) -> None:
    db.add(
        AuditLog(
            admin_id=actor.id,
            action="passkey.partner_workspace_policy.updated",
            entity_type="partner_workspace",
            entity_id=str(workspace_id),
            old_value=previous_payload,
            new_value={**next_payload, "change_reason": change_reason},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    await db.flush()


def _is_active(credential: PasskeyCredentialModel) -> bool:
    return credential.status == "active" and credential.revoked_at is None and credential.deleted_at is None


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _credential_response(credential: PasskeyCredentialModel) -> PasskeyComplianceCredentialResponse:
    return PasskeyComplianceCredentialResponse(
        id=credential.id,
        label=credential.label,
        status=credential.status,
        realm_key=credential.realm_key,
        principal_class=credential.principal_class,
        principal_subject=credential.principal_subject,
        surface=credential.surface,
        rp_id=credential.rp_id,
        credential_id_hash_prefix=credential.credential_id_hash[:12],
        credential_type=credential.credential_type,
        device_type=credential.device_type,
        transports=list(credential.transports or []),
        backed_up=credential.backed_up,
        user_verified=credential.user_verified,
        clone_suspected_at=credential.clone_suspected_at,
        created_at=credential.created_at,
        last_used_at=credential.last_used_at,
        revoked_at=credential.revoked_at,
    )


def _summary(credentials: list[PasskeyCredentialModel]) -> PasskeyComplianceSummaryResponse:
    now = datetime.now(UTC)
    active_credentials = [credential for credential in credentials if _is_active(credential)]
    revoked_credentials = [
        credential for credential in credentials if credential.status == "revoked" or credential.revoked_at is not None
    ]
    principals_with_active = {
        (credential.principal_class, credential.principal_subject) for credential in active_credentials
    }
    stale_credentials = 0
    for credential in active_credentials:
        last_seen = _aware(credential.last_used_at) or _aware(credential.created_at)
        if last_seen is not None and now - last_seen > _STALE_CREDENTIAL_AFTER:
            stale_credentials += 1

    return PasskeyComplianceSummaryResponse(
        active_credentials=len(active_credentials),
        revoked_credentials=len(revoked_credentials),
        clone_suspected_credentials=sum(1 for credential in credentials if credential.clone_suspected_at is not None),
        principals_with_active_passkeys=len(principals_with_active),
        stale_credentials=stale_credentials,
        generated_at=now,
    )


async def _get_default_partner_realm(db: AsyncSession) -> AuthRealmModel:
    realm = await AuthRealmRepository(db).get_default_realm("partner")
    if realm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner auth realm not configured")
    return realm


def _operator_compliance(
    *,
    workspace_id: UUID,
    memberships: list[PartnerAccountUserModel],
    credentials: list[PasskeyCredentialModel],
) -> PartnerWorkspacePasskeyOperatorComplianceResponse:
    active_subjects = {
        str(membership.admin_user_id)
        for membership in memberships
        if membership.membership_status == "active"
    }
    subjects_with_active_passkeys = {
        credential.principal_subject
        for credential in credentials
        if credential.principal_subject in active_subjects and _is_active(credential)
    }
    missing = active_subjects - subjects_with_active_passkeys
    return PartnerWorkspacePasskeyOperatorComplianceResponse(
        workspace_id=workspace_id,
        active_members=len(active_subjects),
        operators_with_active_passkeys=len(subjects_with_active_passkeys),
        operators_missing_active_passkeys=len(missing),
    )


async def _partner_workspace_passkey_context(
    *,
    db: AsyncSession,
    access: PartnerWorkspaceAccess,
) -> tuple[
    AuthRealmModel,
    PartnerWorkspaceProfileModel,
    list[PartnerAccountUserModel],
    list[PasskeyCredentialModel],
]:
    partner_realm = await _get_default_partner_realm(db)
    profile = await PartnerWorkspaceProfileRepository(db).get_or_create(access.workspace.id)
    memberships = await PartnerAccountRepository(db).list_memberships(access.workspace.id)
    member_subjects = [str(membership.admin_user_id) for membership in memberships]
    credentials = await PasskeyCredentialRepository(db).list_for_principal_subjects(
        auth_realm_id=partner_realm.id,
        principal_class=PrincipalClass.PARTNER_OPERATOR.value,
        principal_subjects=member_subjects,
    )
    return partner_realm, profile, memberships, credentials


async def _require_partner_workspace_passkey_access(
    *,
    workspace_id: UUID,
    current_user: AdminUserModel,
    current_realm,
    db: AsyncSession,
    permission: PartnerPermission,
) -> PartnerWorkspaceAccess:
    if current_realm.realm_type != "partner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner passkey policy requires partner realm",
        )
    access = await resolve_partner_workspace_access(
        workspace_id=workspace_id,
        current_user=current_user,
        db=db,
    )
    if access.is_internal_admin_override:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner passkey policy requires workspace membership",
        )
    await enforce_partner_workspace_permission(
        access=access,
        permission=permission,
        current_user=current_user,
        db=db,
    )
    return access


def _partner_workspace_policy_response(
    *,
    access: PartnerWorkspaceAccess,
    partner_realm: AuthRealmModel,
    profile: PartnerWorkspaceProfileModel,
    memberships: list[PartnerAccountUserModel],
    credentials: list[PasskeyCredentialModel],
) -> PartnerWorkspacePasskeyPolicyResponse:
    operator_compliance = _operator_compliance(
        workspace_id=access.workspace.id,
        memberships=memberships,
        credentials=credentials,
    )
    return PartnerWorkspacePasskeyPolicyResponse(
        workspace_id=access.workspace.id,
        workspace_key=access.workspace.account_key,
        workspace_status=access.workspace.status,
        workspace_passkeys_preferred=profile.prefer_passkeys,
        workspace_mfa_required=profile.require_mfa_for_workspace,
        workspace_policy_updated_at=profile.updated_at,
        policy=_policy_response(surface="partner", realm_key=partner_realm.realm_key),
        operator_compliance=operator_compliance,
    )


@router.get("/security/passkeys/policy", response_model=PasskeyPolicyResponse)
async def get_admin_passkey_policy(
    _current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    current_realm=Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
) -> PasskeyPolicyResponse:
    _repo, _service, config_model, admin_policy = await _get_admin_policy_state(db)
    policy = _policy_response(
        surface="admin",
        realm_key=current_realm.realm_key,
        admin_policy=admin_policy,
        config_model=config_model,
    )
    _track("admin_policy", "success")
    return policy


@router.patch("/security/passkeys/policy", response_model=PasskeyPolicyResponse)
async def update_admin_passkey_policy(
    payload: UpdateAdminPasskeyPolicyRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    current_realm=Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PasskeyPolicyResponse:
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_user.id),
        principal_class=get_principal_type_for_realm(current_realm),
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action="admin.passkeys.policy.update",
    )
    if payload.admin_counts_as_mfa is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="adminCountsAsMfa is not available until passkey-as-MFA enforcement is approved",
        )
    _repo, service, config_model, previous_config = await _get_admin_policy_state(db)
    previous_payload = _admin_policy_payload(previous_config)
    updates = payload.model_dump(
        exclude={"change_reason"},
        exclude_none=True,
        exclude_unset=True,
    )
    next_payload = {**previous_payload, **updates}
    await service.set(
        PASSKEY_ADMIN_POLICY_CONFIG_KEY,
        next_payload,
        updated_by=current_user.id,
        description=(
            config_model.description
            if config_model is not None and config_model.description
            else _PASSKEY_ADMIN_POLICY_CONFIG_DESCRIPTION
        ),
    )
    updated_model = await SystemConfigRepository(db).get_by_key(PASSKEY_ADMIN_POLICY_CONFIG_KEY)
    updated_config = await ConfigService(SystemConfigRepository(db)).get_passkey_admin_policy_config()
    change_reason = _normalize_optional_text(payload.change_reason)
    await _write_admin_policy_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        previous_payload=previous_payload,
        next_payload=_admin_policy_payload(updated_config),
        change_reason=change_reason,
    )
    _track("admin_policy_update", "success")
    return _policy_response(
        surface="admin",
        realm_key=current_realm.realm_key,
        admin_policy=updated_config,
        config_model=updated_model,
    )


@router.get("/security/passkeys/compliance", response_model=PasskeyComplianceResponse)
async def get_admin_passkey_compliance(
    _current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    current_realm=Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PasskeyComplianceResponse:
    _repo, _service, config_model, admin_policy = await _get_admin_policy_state(db)
    credentials = await PasskeyCredentialRepository(db).list_for_realm(
        auth_realm_id=current_realm.auth_realm.id,
        principal_class=PrincipalClass.ADMIN.value,
        limit=limit,
        offset=offset,
    )
    _track("admin_compliance", "success")
    logger.info(
        "Admin passkey compliance listed",
        extra={"realm_key": current_realm.realm_key, "credential_count": len(credentials)},
    )
    return PasskeyComplianceResponse(
        policy=_policy_response(
            surface="admin",
            realm_key=current_realm.realm_key,
            admin_policy=admin_policy,
            config_model=config_model,
        ),
        summary=_summary(credentials),
        credentials=[_credential_response(credential) for credential in credentials],
    )


@router.get(
    "/partner-workspaces/{workspace_id}/security/passkeys/policy",
    response_model=PartnerWorkspacePasskeyPolicyResponse,
)
async def get_partner_workspace_passkey_policy(
    workspace_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspacePasskeyPolicyResponse:
    access = await _require_partner_workspace_passkey_access(
        workspace_id=workspace_id,
        current_user=current_user,
        current_realm=current_realm,
        db=db,
        permission=PartnerPermission.WORKSPACE_READ,
    )
    partner_realm, profile, memberships, credentials = await _partner_workspace_passkey_context(db=db, access=access)
    _track("partner_workspace_policy", "success")
    return _partner_workspace_policy_response(
        access=access,
        partner_realm=partner_realm,
        profile=profile,
        memberships=memberships,
        credentials=credentials,
    )


@router.patch(
    "/partner-workspaces/{workspace_id}/security/passkeys/policy",
    response_model=PartnerWorkspacePasskeyPolicyResponse,
)
async def update_partner_workspace_passkey_policy(
    workspace_id: UUID,
    payload: UpdatePartnerWorkspacePasskeyPolicyRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> PartnerWorkspacePasskeyPolicyResponse:
    access = await _require_partner_workspace_passkey_access(
        workspace_id=workspace_id,
        current_user=current_user,
        current_realm=current_realm,
        db=db,
        permission=PartnerPermission.OPERATIONS_WRITE,
    )
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_user.id),
        principal_class=get_principal_type_for_realm(current_realm),
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=f"partner.passkeys.policy.update:{access.workspace.id}",
    )
    profile_repo = PartnerWorkspaceProfileRepository(db)
    profile = await profile_repo.get_or_create(access.workspace.id)
    previous_payload = {
        "prefer_passkeys": profile.prefer_passkeys,
        "require_mfa_for_workspace": profile.require_mfa_for_workspace,
    }
    updates = payload.model_dump(
        exclude={"change_reason"},
        exclude_none=True,
        exclude_unset=True,
    )
    if "prefer_passkeys" in updates:
        profile.prefer_passkeys = bool(updates["prefer_passkeys"])
    if "require_mfa_for_workspace" in updates:
        profile.require_mfa_for_workspace = bool(updates["require_mfa_for_workspace"])
    await profile_repo.update(profile)
    next_payload = {
        "prefer_passkeys": profile.prefer_passkeys,
        "require_mfa_for_workspace": profile.require_mfa_for_workspace,
    }
    await _write_partner_policy_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        workspace_id=access.workspace.id,
        previous_payload=previous_payload,
        next_payload=next_payload,
        change_reason=_normalize_optional_text(payload.change_reason),
    )
    partner_realm, refreshed_profile, memberships, credentials = await _partner_workspace_passkey_context(
        db=db,
        access=access,
    )
    _track("partner_workspace_policy_update", "success")
    return _partner_workspace_policy_response(
        access=access,
        partner_realm=partner_realm,
        profile=refreshed_profile,
        memberships=memberships,
        credentials=credentials,
    )


@router.get(
    "/partner-workspaces/{workspace_id}/security/passkeys/compliance",
    response_model=PartnerWorkspacePasskeyComplianceResponse,
)
async def get_partner_workspace_passkey_compliance(
    workspace_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    current_realm=Depends(get_request_web_auth_realm),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspacePasskeyComplianceResponse:
    access = await _require_partner_workspace_passkey_access(
        workspace_id=workspace_id,
        current_user=current_user,
        current_realm=current_realm,
        db=db,
        permission=PartnerPermission.WORKSPACE_READ,
    )
    partner_realm, profile, memberships, credentials = await _partner_workspace_passkey_context(db=db, access=access)
    operator_compliance = _operator_compliance(
        workspace_id=access.workspace.id,
        memberships=memberships,
        credentials=credentials,
    )
    _track("partner_workspace_compliance", "success")
    logger.info(
        "Partner workspace passkey compliance listed",
        extra={
            "workspace_id": str(access.workspace.id),
            "workspace_status": access.workspace.status,
            "credential_count": len(credentials),
        },
    )
    return PartnerWorkspacePasskeyComplianceResponse(
        workspace_id=access.workspace.id,
        workspace_key=access.workspace.account_key,
        workspace_status=access.workspace.status,
        workspace_passkeys_preferred=profile.prefer_passkeys,
        workspace_mfa_required=profile.require_mfa_for_workspace,
        workspace_policy_updated_at=profile.updated_at,
        policy=_policy_response(surface="partner", realm_key=partner_realm.realm_key),
        operator_compliance=operator_compliance,
        summary=_summary(credentials),
        credentials=[_credential_response(credential) for credential in credentials],
    )
