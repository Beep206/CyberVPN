"""Admin customer-support routes for timeline, notes, VPN access, and recovery actions."""

import logging
import secrets
import string
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptService,
    remnawave_create_request_hash,
    remnawave_customer_create_key,
)
from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    persist_runtime_mapped_mobile_identity,
    resolve_exact_mapped_mobile_user_ref,
)
from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.customer_subscriptions import ListCustomerSubscriptionsUseCase
from src.application.use_cases.subscriptions.stage1_manual_subscription import (
    STAGE1_MANUAL_SUBSCRIPTION_ACTION,
    Stage1ManualSubscriptionError,
    Stage1ManualSubscriptionService,
    build_stage1_manual_subscription_request,
)
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.customer_staff_note_model import CustomerStaffNoteModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.customer_staff_note_repo import CustomerStaffNoteRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileDeviceRepository, MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.database.repositories.withdrawal_repo import WithdrawalRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.stage1_manual_subscription_gateway import (
    RemnawaveStage1ManualSubscriptionGateway,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.customer_subscriptions.schemas import (
    CustomerSubscriptionListResponse,
    CustomerSubscriptionSummaryResponse,
)
from src.presentation.api.v1.subscriptions.credential_access import read_customer_vpn_credentials_as_admin
from src.presentation.dependencies.auth import (
    CurrentPrincipalActor,
    get_current_active_user,
    get_current_principal_actor,
)
from src.presentation.dependencies.auth_realms import get_request_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .audit import write_required_admin_audit_entry
from .customer_support_schemas import (
    AdminBulkDeviceRevokeResponse,
    AdminCreateCustomerStaffNoteRequest,
    AdminCustomerCredentialRegenerationRequest,
    AdminCustomerCredentialRegenerationResponse,
    AdminCustomerManualSubscriptionRequest,
    AdminCustomerManualSubscriptionResponse,
    AdminCustomerPasswordResetRequest,
    AdminCustomerPasswordResetResponse,
    AdminCustomerStaffNoteResponse,
    AdminCustomerSubscriptionResyncResponse,
    AdminCustomerSupportActionRequest,
    AdminCustomerTimelineItemResponse,
    AdminCustomerTimelineResponse,
    AdminCustomerVpnUserResponse,
    AdminSupportActorSummary,
)
from .mobile_users import _serialize_mobile_device
from .mobile_users_schemas import AdminMobileDeviceResponse

router = APIRouter(prefix="/admin/mobile-users", tags=["admin", "customer-support"])
logger = logging.getLogger(__name__)

TEMP_PASSWORD_SPECIALS = "!@#$%^&*()-_=+[]{}"  # noqa: S105 - alphabet for generated temporary passwords.
REDACTED_ADMIN_URL = "[REDACTED]"


def _actor_label(actor: AdminUserModel | None) -> str | None:
    if actor is None:
        return None

    return actor.display_name or actor.login or actor.email


def _serialize_note(
    note: CustomerStaffNoteModel,
    actors_by_id: dict[UUID, AdminUserModel],
) -> AdminCustomerStaffNoteResponse:
    actor = actors_by_id.get(note.admin_id) if note.admin_id else None
    return AdminCustomerStaffNoteResponse(
        id=note.id,
        user_id=note.user_id,
        admin_id=note.admin_id,
        category=note.category,
        note=note.note,
        created_at=note.created_at,
        updated_at=note.updated_at,
        author=(
            AdminSupportActorSummary(
                id=actor.id,
                login=actor.login,
                email=actor.email,
                display_name=actor.display_name,
            )
            if actor is not None
            else None
        ),
    )


def _sort_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _write_audit_entry(
    *,
    db: AsyncSession,
    action: str,
    user_id: UUID,
    actor: AdminUserModel,
    request: Request,
    details: Mapping[str, object] | None = None,
) -> None:
    await _write_required_audit_entry(
        db=db,
        action=action,
        user_id=user_id,
        actor=actor,
        request=request,
        details=details,
    )


async def _write_required_audit_entry(
    *,
    db: AsyncSession,
    action: str,
    user_id: UUID,
    actor: AdminUserModel,
    request: Request,
    details: Mapping[str, object] | None = None,
) -> None:
    await write_required_admin_audit_entry(
        db=db,
        action=action,
        resource_type="mobile_user",
        resource_id=user_id,
        actor=actor,
        request=request,
        details=details,
    )


async def _require_mobile_user(
    user_id: UUID,
    db: AsyncSession,
) -> MobileUserModel:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id_with_devices(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")
    return user


async def _resolve_customer_vpn_ref(
    db: AsyncSession,
    user: MobileUserModel,
) -> RemnawaveUserRef | None:
    try:
        user_ref = await resolve_exact_mapped_mobile_user_ref(db, user)
    except RemnawaveIdentityAccessConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Remnawave identity reconciliation required",
        ) from exc
    return user_ref


async def _require_customer_vpn_ref(
    db: AsyncSession,
    user: MobileUserModel,
) -> RemnawaveUserRef:
    user_ref = await _resolve_customer_vpn_ref(db, user)
    if user_ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer has no linked VPN user")
    return user_ref


def _generate_temporary_password(length: int = 18) -> str:
    if length < 12:
        length = 12

    alphabet = string.ascii_letters + string.digits + TEMP_PASSWORD_SPECIALS
    password_chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(TEMP_PASSWORD_SPECIALS),
    ]
    password_chars.extend(secrets.choice(alphabet) for _ in range(length - len(password_chars)))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _redact_admin_url(value: str | None) -> str | None:
    return REDACTED_ADMIN_URL if value else None


def _optional_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _serialize_vpn_user(
    remnawave_user_id: int | None,
    remnawave_uuid: str | None,
    vpn_user,
) -> AdminCustomerVpnUserResponse:
    parsed_uuid = _optional_uuid(remnawave_uuid)

    if vpn_user is None:
        return AdminCustomerVpnUserResponse(
            exists=False,
            remnawave_user_id=remnawave_user_id,
            remnawave_uuid=parsed_uuid,
        )

    return AdminCustomerVpnUserResponse(
        exists=True,
        remnawave_user_id=vpn_user.remnawave_id or remnawave_user_id,
        remnawave_uuid=parsed_uuid,
        username=vpn_user.username,
        email=vpn_user.email,
        status=vpn_user.status,
        # These identifiers are live bearer material, not support metadata.
        short_uuid=None,
        subscription_uuid=None,
        expire_at=vpn_user.expire_at,
        traffic_limit_bytes=vpn_user.traffic_limit_bytes,
        used_traffic_bytes=vpn_user.used_traffic_bytes,
        created_at=vpn_user.created_at,
        updated_at=vpn_user.updated_at,
        telegram_id=vpn_user.telegram_id,
    )


def _resolve_customer_auth_realm_id(user: MobileUserModel) -> UUID:
    return user.auth_realm_id or stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"]))


def _serialize_customer_subscription_summary(item) -> CustomerSubscriptionSummaryResponse:
    return CustomerSubscriptionSummaryResponse(
        subscription_key=item.subscription_key,
        kind=item.kind,
        status=item.status,
        display_name=item.display_name,
        plan_uuid=item.plan_uuid,
        plan_code=item.plan_code,
        source_type=item.source_type,
        source_order_id=item.source_order_id,
        entitlement_grant_id=item.entitlement_grant_id,
        service_identity_id=item.service_identity_id,
        provider_name=item.provider_name,
        expires_at=item.expires_at,
        created_at=item.created_at,
        effective_entitlements=item.effective_entitlements,
        invite_bundle=item.invite_bundle,
        is_trial=item.is_trial,
        addons=item.addons,
        can_manage=item.can_manage,
        can_deliver_config=item.can_deliver_config,
        management_scope=item.management_scope,
    )


@router.get("/{user_id}/notes", response_model=list[AdminCustomerStaffNoteResponse])
async def list_customer_staff_notes(
    user_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> list[AdminCustomerStaffNoteResponse]:
    await _require_mobile_user(user_id, db)

    notes_repo = CustomerStaffNoteRepository(db)
    admin_repo = AdminUserRepository(db)

    notes = await notes_repo.list_by_user(user_id, offset=offset, limit=limit)
    actors = await admin_repo.list_by_ids([note.admin_id for note in notes if note.admin_id is not None])
    actors_by_id = {actor.id: actor for actor in actors}

    route_operations_total.labels(route="admin_customer_support", action="notes_list", status="success").inc()
    return [_serialize_note(note, actors_by_id) for note in notes]


@router.post(
    "/{user_id}/notes",
    response_model=AdminCustomerStaffNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer_staff_note(
    user_id: UUID,
    body: AdminCreateCustomerStaffNoteRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminCustomerStaffNoteResponse:
    await _require_mobile_user(user_id, db)
    note_text = body.note.strip()
    if not note_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Note cannot be empty")

    notes_repo = CustomerStaffNoteRepository(db)
    note = await notes_repo.create(
        CustomerStaffNoteModel(
            user_id=user_id,
            admin_id=current_user.id,
            category=body.category,
            note=note_text,
        )
    )

    await _write_audit_entry(
        db=db,
        action="customer_staff_note_created",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "note_id": str(note.id),
            "category": note.category,
            "note_length": len(note.note),
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="notes_create", status="success").inc()
    return _serialize_note(note, {current_user.id: current_user})


@router.get("/{user_id}/customer-subscriptions", response_model=CustomerSubscriptionListResponse)
async def list_admin_customer_subscriptions(
    user_id: UUID,
    selected_subscription_key: str | None = Query(None, min_length=1, max_length=220),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> CustomerSubscriptionListResponse:
    """Return all customer subscriptions for support-side selected-subscription inspection."""
    user = await _require_mobile_user(user_id, db)
    auth_realm_id = _resolve_customer_auth_realm_id(user)
    result = await ListCustomerSubscriptionsUseCase(db).execute(
        customer_account_id=user.id,
        auth_realm_id=auth_realm_id,
        selected_subscription_key=selected_subscription_key,
    )

    route_operations_total.labels(
        route="admin_customer_support",
        action="customer_subscriptions_list",
        status="success",
    ).inc()
    return CustomerSubscriptionListResponse(
        customer_account_id=result.customer_account_id,
        auth_realm_id=result.auth_realm_id,
        selected_subscription_key=result.selected_subscription_key,
        default_subscription_key=result.default_subscription_key,
        items=[_serialize_customer_subscription_summary(item) for item in result.items],
        limitations=result.limitations,
    )


@router.get("/{user_id}/vpn-user", response_model=AdminCustomerVpnUserResponse)
async def get_customer_vpn_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminCustomerVpnUserResponse:
    user = await _require_mobile_user(user_id, db)
    gateway = RemnawaveUserGateway(client=client)
    user_ref = await _resolve_customer_vpn_ref(db, user)

    vpn_user = await gateway.get_by_ref(user_ref) if user_ref is not None else None

    route_operations_total.labels(route="admin_customer_support", action="vpn_get", status="success").inc()
    return _serialize_vpn_user(getattr(user, "remnawave_user_id", None), user.remnawave_uuid, vpn_user)


@router.post("/{user_id}/vpn-user/enable", response_model=AdminCustomerVpnUserResponse)
async def enable_customer_vpn_user(
    user_id: UUID,
    body: AdminCustomerSupportActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminCustomerVpnUserResponse:
    user = await _require_mobile_user(user_id, db)
    user_ref = await _require_customer_vpn_ref(db, user)

    gateway = RemnawaveUserGateway(client=client)
    await gateway.update(user_ref, status=UserStatus.ACTIVE)
    vpn_user = await gateway.get_by_ref(user_ref)

    await _write_audit_entry(
        db=db,
        action="customer_vpn_enabled",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "remnawave_user_id": getattr(user, "remnawave_user_id", None),
            "remnawave_uuid": user.remnawave_uuid,
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="vpn_enable", status="success").inc()
    return _serialize_vpn_user(getattr(user, "remnawave_user_id", None), user.remnawave_uuid, vpn_user)


@router.post("/{user_id}/vpn-user/disable", response_model=AdminCustomerVpnUserResponse)
async def disable_customer_vpn_user(
    user_id: UUID,
    body: AdminCustomerSupportActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminCustomerVpnUserResponse:
    user = await _require_mobile_user(user_id, db)
    user_ref = await _require_customer_vpn_ref(db, user)

    gateway = RemnawaveUserGateway(client=client)
    await gateway.update(user_ref, status=UserStatus.DISABLED)
    vpn_user = await gateway.get_by_ref(user_ref)

    await _write_audit_entry(
        db=db,
        action="customer_vpn_disabled",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "remnawave_user_id": getattr(user, "remnawave_user_id", None),
            "remnawave_uuid": user.remnawave_uuid,
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="vpn_disable", status="success").inc()
    return _serialize_vpn_user(getattr(user, "remnawave_user_id", None), user.remnawave_uuid, vpn_user)


@router.post(
    "/{user_id}/vpn-user/regenerate-credentials",
    response_model=AdminCustomerCredentialRegenerationResponse,
)
async def regenerate_customer_vpn_credentials(
    user_id: UUID,
    body: AdminCustomerCredentialRegenerationRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.VPN_CREDENTIAL_REGENERATE)),
) -> AdminCustomerCredentialRegenerationResponse:
    user = await _require_mobile_user(user_id, db)
    await _require_customer_vpn_ref(db, user)

    # Remnawave exposes no idempotency key and a password-only rotation has no
    # authoritative readback postcondition. Keep the operator surface closed
    # until a durable per-customer attempt receipt and settlement workflow are
    # deployed; otherwise a retry after a lost response can rotate twice.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="VPN credential regeneration is safety-disabled pending durable reconciliation receipts",
    )


@router.post(
    "/{user_id}/subscription/manual-grant",
    response_model=AdminCustomerManualSubscriptionResponse,
)
async def apply_manual_customer_subscription(
    user_id: UUID,
    body: AdminCustomerManualSubscriptionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.SUBSCRIPTION_CREATE)),
) -> AdminCustomerManualSubscriptionResponse:
    user = await _require_mobile_user(user_id, db)
    user_gateway = RemnawaveUserGateway(client=client)
    current_vpn_user = None
    user_ref = await _resolve_customer_vpn_ref(db, user)

    if user_ref is not None:
        current_vpn_user = await user_gateway.get_by_ref(user_ref)

    current_expires_at = current_vpn_user.expires_at if current_vpn_user is not None else None
    previous_subscription_url = user.subscription_url or (
        current_vpn_user.subscription_url if current_vpn_user is not None else None
    )

    create_attempts: RemnawaveCreateAttemptService | None = None
    create_record = None
    try:
        manual_request = build_stage1_manual_subscription_request(
            customer_account_id=user_id,
            actor_admin_id=current_user.id,
            email=user.email,
            username=user.username,
            telegram_id=user.telegram_id,
            plan_code=body.plan_code,
            reason=body.reason,
            duration_days=body.duration_days,
            current_access_expires_at=current_expires_at,
            traffic_limit_bytes=body.traffic_limit_bytes,
            device_limit=body.device_limit,
            existing_remnawave_user_id=user_ref.id if user_ref is not None else None,
            existing_remnawave_uuid=(
                str(user_ref.legacy_uuid) if user_ref is not None and user_ref.legacy_uuid is not None else None
            ),
            previous_subscription_url=previous_subscription_url,
        )
        if user_ref is None:
            create_attempts = RemnawaveCreateAttemptService(db)
            decision = await create_attempts.begin(
                scope="remnawave-customer:create",
                idempotency_key=remnawave_customer_create_key(user_id),
                request_hash=remnawave_create_request_hash(
                    {
                        "customer_account_id": str(user_id),
                        "plan_code": manual_request.plan_code,
                        "access_expires_at": manual_request.access_expires_at,
                        "traffic_limit_bytes": manual_request.traffic_limit_bytes,
                        "device_limit": manual_request.device_limit,
                    }
                ),
                customer_account_id=user_id,
            )
            if not decision.should_mutate:
                raise RemnawaveCreateAttemptConflict("Manual Remnawave creation requires reconciliation")
            create_record = decision.record
        result = await Stage1ManualSubscriptionService(
            RemnawaveStage1ManualSubscriptionGateway(user_gateway),
        ).apply(manual_request)
    except (Stage1ManualSubscriptionError, RemnawaveCreateAttemptConflict) as exc:
        if create_attempts is not None and create_record is not None:
            await create_attempts.mark_reconciliation_required(create_record)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        if create_attempts is not None and create_record is not None:
            await create_attempts.mark_reconciliation_required(create_record)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual Remnawave creation requires reconciliation",
            ) from exc
        raise

    try:
        persisted_user_ref = await persist_runtime_mapped_mobile_identity(
            db,
            customer=user,
            remnawave_user_id=result.remnawave_user_id,
            remnawave_uuid=result.remnawave_uuid,
            source="admin_customer_support_manual_subscription",
        )
    except RemnawaveIdentityAccessConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Remnawave identity reconciliation required",
        ) from exc
    if create_attempts is not None and create_record is not None:
        await create_attempts.mark_completed(create_record, user_ref=persisted_user_ref)

    user_changed = user_ref != persisted_user_ref
    if result.subscription_url and user.subscription_url != result.subscription_url:
        user.subscription_url = result.subscription_url
        user_changed = True
    if user.status != UserStatus.ACTIVE.value:
        user.status = UserStatus.ACTIVE.value
        user_changed = True
    if not user.is_active:
        user.is_active = True
        user_changed = True

    if user_changed:
        user_repo = MobileUserRepository(db)
        await user_repo.update(user)

    audit_details = result.to_audit_details(reason=body.reason)
    audit_details["previous_subscription_url_present"] = previous_subscription_url is not None
    await _write_required_audit_entry(
        db=db,
        action=STAGE1_MANUAL_SUBSCRIPTION_ACTION,
        user_id=user_id,
        actor=current_user,
        request=request,
        details=audit_details,
    )

    logger.info(
        "Stage 1 manual subscription operation completed",
        extra={"stage1_manual_subscription": result.to_safe_dict()},
    )
    route_operations_total.labels(
        route="admin_customer_support",
        action="subscription_manual_grant",
        status="success",
    ).inc()
    return AdminCustomerManualSubscriptionResponse(
        user_id=user_id,
        remnawave_user_id=result.remnawave_user_id,
        remnawave_uuid=_optional_uuid(result.remnawave_uuid),
        status=result.status,
        operation=result.operation,
        duration_days=result.duration_days,
        previous_expires_at=result.previous_expires_at,
        expires_at=result.expires_at,
        created=result.created,
        subscription_url_changed=result.subscription_url_changed,
        config_delivery_required=True,
        audit_action=STAGE1_MANUAL_SUBSCRIPTION_ACTION,
    )


@router.delete("/{user_id}/devices/{device_id}", response_model=AdminMobileDeviceResponse)
async def revoke_customer_device(
    user_id: UUID,
    device_id: UUID,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminMobileDeviceResponse:
    await _require_mobile_user(user_id, db)

    device_repo = MobileDeviceRepository(db)
    device = await device_repo.get_by_id_for_user(device_id, user_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    response = _serialize_mobile_device(device)
    await device_repo.delete(device)

    await _write_audit_entry(
        db=db,
        action="customer_device_revoked",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "device_id": str(response.id),
            "platform": response.platform,
            "device_model": response.device_model,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="device_revoke", status="success").inc()
    return response


@router.post("/{user_id}/devices/revoke-all", response_model=AdminBulkDeviceRevokeResponse)
async def revoke_all_customer_devices(
    user_id: UUID,
    body: AdminCustomerSupportActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminBulkDeviceRevokeResponse:
    await _require_mobile_user(user_id, db)

    device_repo = MobileDeviceRepository(db)
    devices = await device_repo.get_user_devices(user_id)
    revoked_devices = [_serialize_mobile_device(device) for device in devices]

    if not revoked_devices:
        route_operations_total.labels(route="admin_customer_support", action="device_revoke_all", status="noop").inc()
        return AdminBulkDeviceRevokeResponse(user_id=user_id, revoked_count=0, revoked_devices=[])

    for device in devices:
        await device_repo.delete(device)

    await _write_audit_entry(
        db=db,
        action="customer_devices_revoked_all",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "revoked_count": len(revoked_devices),
            "device_models_csv": ", ".join(sorted({device.device_model for device in revoked_devices})),
            "platforms_csv": ", ".join(sorted({device.platform for device in revoked_devices})),
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="device_revoke_all", status="success").inc()
    return AdminBulkDeviceRevokeResponse(
        user_id=user_id,
        revoked_count=len(revoked_devices),
        revoked_devices=revoked_devices,
    )


@router.post("/{user_id}/credentials/reset-password", response_model=AdminCustomerPasswordResetResponse)
async def reset_customer_password(
    user_id: UUID,
    body: AdminCustomerPasswordResetRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminCustomerPasswordResetResponse:
    user = await _require_mobile_user(user_id, db)

    password_mode = "generated" if body.generate_temporary_password else "provided"
    next_password = body.new_password or _generate_temporary_password()
    auth_service = AuthService()

    user.password_hash = await auth_service.hash_password(next_password)
    user_repo = MobileUserRepository(db)
    await user_repo.update(user)

    devices_revoked = 0
    if body.revoke_all_devices:
        device_repo = MobileDeviceRepository(db)
        devices = await device_repo.get_user_devices(user_id)
        devices_revoked = len(devices)
        for device in devices:
            await device_repo.delete(device)

    await _write_audit_entry(
        db=db,
        action="customer_password_reset",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "password_mode": password_mode,
            "device_sessions_cleared": body.revoke_all_devices,
            "devices_revoked": devices_revoked,
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="password_reset", status="success").inc()
    return AdminCustomerPasswordResetResponse.model_validate(
        {
            "user_id": user_id,
            "password_mode": password_mode,
            "device_sessions_cleared": body.revoke_all_devices,
            "devices_revoked": devices_revoked,
            "generated_password": next_password if body.generate_temporary_password else None,
        }
    )


@router.post("/{user_id}/subscription/resync", response_model=AdminCustomerSubscriptionResyncResponse)
async def resync_customer_subscription(
    user_id: UUID,
    body: AdminCustomerSupportActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    current_actor: CurrentPrincipalActor = Depends(get_current_principal_actor),
    current_realm: RealmResolution = Depends(get_request_auth_realm),
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    redis_client: redis.Redis = Depends(get_redis),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminCustomerSubscriptionResyncResponse:
    config = await read_customer_vpn_credentials_as_admin(
        customer_id=user_id,
        request=request,
        actor=current_actor,
        current_realm=current_realm,
        db=db,
        client=client,
        redis_client=redis_client,
    )
    user = await _require_mobile_user(user_id, db)
    subscription_url = config.get("subscription_url")
    if not isinstance(subscription_url, str) or not subscription_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No upstream subscription URL available")

    previous_subscription_url = user.subscription_url
    changed = previous_subscription_url != subscription_url

    if changed:
        user.subscription_url = subscription_url
        user_repo = MobileUserRepository(db)
        await user_repo.update(user)

    config_client_type = config.get("client_type")
    links = config.get("links")
    links_count = len(links) if isinstance(links, list) else 0

    await _write_audit_entry(
        db=db,
        action="customer_subscription_resynced",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "previous_subscription_url_present": previous_subscription_url is not None,
            "stored_subscription_url_present": True,
            "upstream_subscription_url_present": True,
            "changed": changed,
            "config_available": bool(config.get("config") or config.get("config_string")),
            "config_client_type": config_client_type if isinstance(config_client_type, str) else None,
            "links_count": links_count,
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(
        route="admin_customer_support",
        action="subscription_resync",
        status="success" if changed else "noop",
    ).inc()
    return AdminCustomerSubscriptionResyncResponse(
        user_id=user_id,
        previous_subscription_url=_redact_admin_url(previous_subscription_url),
        stored_subscription_url=REDACTED_ADMIN_URL,
        upstream_subscription_url=REDACTED_ADMIN_URL,
        previous_subscription_url_present=previous_subscription_url is not None,
        stored_subscription_url_present=True,
        upstream_subscription_url_present=True,
        changed=changed,
        config_available=bool(config.get("config") or config.get("config_string")),
        config_client_type=config_client_type if isinstance(config_client_type, str) else None,
        links_count=links_count,
    )


@router.get("/{user_id}/timeline", response_model=AdminCustomerTimelineResponse)
async def get_customer_timeline(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminCustomerTimelineResponse:
    user = await _require_mobile_user(user_id, db)

    payment_repo = PaymentRepository(db)
    wallet_repo = WalletRepository(db)
    withdrawal_repo = WithdrawalRepository(db)
    notes_repo = CustomerStaffNoteRepository(db)
    admin_repo = AdminUserRepository(db)
    audit_repo = AuditLogRepository(db)

    payments = await payment_repo.get_by_user_uuid(user_id, limit=limit)
    wallet_transactions = await wallet_repo.get_transactions(user_id, limit=limit)
    withdrawals = await withdrawal_repo.get_by_user(user_id, limit=limit)
    notes = await notes_repo.list_by_user(user_id, limit=limit)
    audit_logs = await audit_repo.get_by_entity("mobile_user", str(user_id), limit=limit)

    actor_ids = {note.admin_id for note in notes if note.admin_id is not None} | {
        log.admin_id for log in audit_logs if log.admin_id is not None
    }
    actors = await admin_repo.list_by_ids(list(actor_ids))
    actors_by_id = {actor.id: actor for actor in actors}

    items: list[AdminCustomerTimelineItemResponse] = []

    for payment in payments:
        items.append(
            AdminCustomerTimelineItemResponse(
                id=str(payment.id),
                kind="payment",
                occurred_at=payment.created_at,
                title=f"Payment via {payment.provider}",
                description=f"Subscription days: {payment.subscription_days}",
                status=payment.status,
                amount=float(payment.amount),
                currency=payment.currency,
                metadata={
                    "plan_id": str(payment.plan_id) if payment.plan_id else None,
                    "promo_code_id": str(payment.promo_code_id) if payment.promo_code_id else None,
                    "partner_code_id": str(payment.partner_code_id) if payment.partner_code_id else None,
                },
            )
        )

    for tx in wallet_transactions:
        items.append(
            AdminCustomerTimelineItemResponse(
                id=str(tx.id),
                kind="wallet_transaction",
                occurred_at=tx.created_at,
                title=f"Wallet {tx.type}",
                description=tx.description or tx.reason,
                status=tx.reason,
                amount=float(tx.amount),
                currency=tx.currency,
                metadata={
                    "balance_after": float(tx.balance_after),
                    "reference_type": tx.reference_type,
                    "reference_id": str(tx.reference_id) if tx.reference_id else None,
                },
            )
        )

    for withdrawal in withdrawals:
        items.append(
            AdminCustomerTimelineItemResponse(
                id=str(withdrawal.id),
                kind="withdrawal",
                occurred_at=withdrawal.created_at,
                title="Withdrawal request",
                description=withdrawal.admin_note,
                status=withdrawal.status,
                amount=float(withdrawal.amount),
                currency=withdrawal.currency,
                actor_label=(
                    _actor_label(actors_by_id.get(withdrawal.processed_by)) if withdrawal.processed_by else None
                ),
                metadata={
                    "method": withdrawal.method,
                    "processed_at": withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
                },
            )
        )

    for device in user.devices:
        occurred_at = device.last_active_at or device.registered_at
        items.append(
            AdminCustomerTimelineItemResponse(
                id=str(device.id),
                kind="device",
                occurred_at=occurred_at,
                title=f"Device {device.platform}",
                description=f"{device.device_model} / {device.app_version}",
                status="last_active" if device.last_active_at else "registered",
                metadata={
                    "device_id": device.device_id,
                    "platform_id": device.platform_id,
                    "os_version": device.os_version,
                    "registered_at": device.registered_at.isoformat(),
                    "last_active_at": device.last_active_at.isoformat() if device.last_active_at else None,
                },
            )
        )

    for note in notes:
        items.append(
            AdminCustomerTimelineItemResponse(
                id=str(note.id),
                kind="note",
                occurred_at=note.created_at,
                title=f"Staff note / {note.category}",
                description=note.note,
                actor_label=_actor_label(actors_by_id.get(note.admin_id)) if note.admin_id else None,
            )
        )

    for log in audit_logs:
        if log.action == "customer_staff_note_created":
            continue

        items.append(
            AdminCustomerTimelineItemResponse(
                id=str(log.id),
                kind="audit",
                occurred_at=log.created_at,
                title=log.action.replace("_", " "),
                description=None,
                actor_label=_actor_label(actors_by_id.get(log.admin_id)) if log.admin_id else None,
                metadata=log.new_value,
            )
        )

    items.sort(key=lambda item: _sort_datetime(item.occurred_at), reverse=True)

    route_operations_total.labels(route="admin_customer_support", action="timeline_get", status="success").inc()
    return AdminCustomerTimelineResponse(items=items[:limit])
