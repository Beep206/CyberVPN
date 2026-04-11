"""Admin customer-support routes for timeline, notes, VPN access, and recovery actions."""

import secrets
import string
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.services.auth_service import AuthService
from src.domain.enums import UserStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.customer_staff_note_model import CustomerStaffNoteModel
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.customer_staff_note_repo import CustomerStaffNoteRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileDeviceRepository, MobileUserRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.database.repositories.withdrawal_repo import WithdrawalRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .customer_support_schemas import (
    AdminBulkDeviceRevokeResponse,
    AdminCreateCustomerStaffNoteRequest,
    AdminCustomerPasswordResetRequest,
    AdminCustomerPasswordResetResponse,
    AdminCustomerSubscriptionResyncResponse,
    AdminCustomerStaffNoteResponse,
    AdminCustomerSupportActionRequest,
    AdminCustomerTimelineItemResponse,
    AdminCustomerTimelineResponse,
    AdminCustomerVpnUserResponse,
    AdminSupportActorSummary,
)
from .mobile_users_schemas import AdminMobileDeviceResponse
from .mobile_users import build_mobile_user_subscription_snapshot

router = APIRouter(prefix="/admin/mobile-users", tags=["admin", "customer-support"])

TEMP_PASSWORD_SPECIALS = "!@#$%^&*()-_=+[]{}"


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
    details: dict[str, object] | None = None,
) -> None:
    audit_repo = AuditLogRepository(db)
    try:
        await audit_repo.create(
            event_type=action,
            actor_id=actor.id,
            resource_type="mobile_user",
            resource_id=str(user_id),
            details=details,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        # Best-effort audit logging; do not fail primary support action.
        return


async def _require_mobile_user(
    user_id: UUID,
    db: AsyncSession,
) -> MobileUserModel:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id_with_devices(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")
    return user


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


def _serialize_vpn_user(remnawave_uuid: str | None, vpn_user) -> AdminCustomerVpnUserResponse:
    parsed_uuid = None
    if remnawave_uuid:
        try:
            parsed_uuid = UUID(remnawave_uuid)
        except ValueError:
            parsed_uuid = None

    if vpn_user is None:
        return AdminCustomerVpnUserResponse(exists=False, remnawave_uuid=parsed_uuid)

    return AdminCustomerVpnUserResponse(
        exists=True,
        remnawave_uuid=parsed_uuid,
        username=vpn_user.username,
        email=vpn_user.email,
        status=vpn_user.status,
        short_uuid=vpn_user.short_uuid,
        subscription_uuid=vpn_user.subscription_uuid,
        expire_at=vpn_user.expire_at,
        traffic_limit_bytes=vpn_user.traffic_limit_bytes,
        used_traffic_bytes=vpn_user.used_traffic_bytes,
        created_at=vpn_user.created_at,
        updated_at=vpn_user.updated_at,
        telegram_id=vpn_user.telegram_id,
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Note cannot be empty")

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


@router.get("/{user_id}/vpn-user", response_model=AdminCustomerVpnUserResponse)
async def get_customer_vpn_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminCustomerVpnUserResponse:
    user = await _require_mobile_user(user_id, db)
    gateway = RemnawaveUserGateway(client=client)

    vpn_user = None
    if user.remnawave_uuid:
        try:
            vpn_user = await gateway.get_by_uuid(UUID(user.remnawave_uuid))
        except ValueError:
            vpn_user = None

    route_operations_total.labels(route="admin_customer_support", action="vpn_get", status="success").inc()
    return _serialize_vpn_user(user.remnawave_uuid, vpn_user)


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
    if not user.remnawave_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer has no linked VPN user")

    gateway = RemnawaveUserGateway(client=client)
    try:
        vpn_uuid = UUID(user.remnawave_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Remnawave UUID") from exc

    await gateway.update(vpn_uuid, status=UserStatus.ACTIVE)
    vpn_user = await gateway.get_by_uuid(vpn_uuid)

    await _write_audit_entry(
        db=db,
        action="customer_vpn_enabled",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "remnawave_uuid": user.remnawave_uuid,
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="vpn_enable", status="success").inc()
    return _serialize_vpn_user(user.remnawave_uuid, vpn_user)


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
    if not user.remnawave_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer has no linked VPN user")

    gateway = RemnawaveUserGateway(client=client)
    try:
        vpn_uuid = UUID(user.remnawave_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Remnawave UUID") from exc

    await gateway.update(vpn_uuid, status=UserStatus.DISABLED)
    vpn_user = await gateway.get_by_uuid(vpn_uuid)

    await _write_audit_entry(
        db=db,
        action="customer_vpn_disabled",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "remnawave_uuid": user.remnawave_uuid,
            "reason_length": len(body.reason.strip()) if body.reason else 0,
        },
    )

    route_operations_total.labels(route="admin_customer_support", action="vpn_disable", status="success").inc()
    return _serialize_vpn_user(user.remnawave_uuid, vpn_user)


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

    response = AdminMobileDeviceResponse.model_validate(device)
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
    revoked_devices = [AdminMobileDeviceResponse.model_validate(device) for device in devices]

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
    return AdminCustomerPasswordResetResponse(
        user_id=user_id,
        password_mode=password_mode,
        device_sessions_cleared=body.revoke_all_devices,
        devices_revoked=devices_revoked,
        generated_password=next_password if body.generate_temporary_password else None,
    )


@router.post("/{user_id}/subscription/resync", response_model=AdminCustomerSubscriptionResyncResponse)
async def resync_customer_subscription(
    user_id: UUID,
    body: AdminCustomerSupportActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminCustomerSubscriptionResyncResponse:
    user = await _require_mobile_user(user_id, db)
    snapshot = await build_mobile_user_subscription_snapshot(user, client)

    if not snapshot.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer subscription snapshot not found")

    if not snapshot.subscription_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No upstream subscription URL available")

    previous_subscription_url = user.subscription_url
    changed = previous_subscription_url != snapshot.subscription_url

    if changed:
        user.subscription_url = snapshot.subscription_url
        user_repo = MobileUserRepository(db)
        await user_repo.update(user)

    await _write_audit_entry(
        db=db,
        action="customer_subscription_resynced",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "previous_subscription_url": previous_subscription_url,
            "stored_subscription_url": snapshot.subscription_url,
            "upstream_subscription_url": snapshot.subscription_url,
            "changed": changed,
            "config_available": snapshot.config_available,
            "config_client_type": snapshot.config_client_type,
            "links_count": len(snapshot.links),
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
        previous_subscription_url=previous_subscription_url,
        stored_subscription_url=snapshot.subscription_url,
        upstream_subscription_url=snapshot.subscription_url,
        changed=changed,
        config_available=snapshot.config_available,
        config_client_type=snapshot.config_client_type,
        links_count=len(snapshot.links),
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

    actor_ids = {
        note.admin_id for note in notes if note.admin_id is not None
    } | {
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
                actor_label=_actor_label(actors_by_id.get(withdrawal.processed_by)) if withdrawal.processed_by else None,
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
