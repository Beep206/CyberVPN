"""Admin routes for mobile user directory and lifecycle management."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .mobile_users_schemas import (
    AdminMobileUserDetailResponse,
    AdminMobileUserListItemResponse,
    AdminMobileUsersListResponse,
    AdminMobileUserSubscriptionSnapshotResponse,
    AdminUpdateMobileUserRequest,
)

router = APIRouter(prefix="/admin/mobile-users", tags=["admin", "mobile-users"])


def _serialize_mobile_user_list_item(
    user: MobileUserModel,
    device_count: int,
) -> AdminMobileUserListItemResponse:
    return AdminMobileUserListItemResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        status=user.status,
        is_active=user.is_active,
        is_partner=user.is_partner,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        remnawave_uuid=user.remnawave_uuid,
        referral_code=user.referral_code,
        referred_by_user_id=user.referred_by_user_id,
        partner_user_id=user.partner_user_id,
        partner_promoted_at=user.partner_promoted_at,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        device_count=device_count,
    )


def _serialize_mobile_user_detail(user: MobileUserModel) -> AdminMobileUserDetailResponse:
    return AdminMobileUserDetailResponse(
        **_serialize_mobile_user_list_item(user, len(user.devices)).model_dump(),
        subscription_url=user.subscription_url,
        updated_at=user.updated_at,
        devices=list(user.devices),
    )


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _compute_days_left(expires_at: datetime | None) -> int | None:
    if expires_at is None:
        return None

    expires_in_utc = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    remaining = expires_in_utc - datetime.now(UTC)
    return max(int(remaining.total_seconds() // 86400), 0)


def _is_placeholder_config_link(link: str) -> bool:
    lowered = link.lower()
    return (
        "00000000-0000-0000-0000-000000000000@0.0.0.0:1" in lowered
        or "no%20hosts%20found" in lowered
        or "check%20hosts%20tab" in lowered
        or "check%20internal%20squads%20tab" in lowered
    )


def _select_primary_subscription_config(
    *,
    links: list[str],
    subscription_url: str | None,
) -> str | None:
    for link in links:
        if link and not _is_placeholder_config_link(link):
            return link

    if subscription_url and not _is_placeholder_config_link(subscription_url):
        return subscription_url

    return None


def _detect_config_client_type(config: str | None) -> str | None:
    if not config:
        return None
    if "://" not in config:
        return "subscription"
    scheme = config.split("://", 1)[0].lower()
    return "subscription" if scheme in {"http", "https"} else scheme


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
        return


@router.get("", response_model=AdminMobileUsersListResponse)
async def list_mobile_users(
    search: str | None = Query(None, description="Search by email, username, telegram, UUID, referral code"),
    status_filter: str | None = Query(None, alias="status", description="Filter by current status"),
    is_active: bool | None = Query(None, description="Filter by activation state"),
    is_partner: bool | None = Query(None, description="Filter by partner state"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminMobileUsersListResponse:
    user_repo = MobileUserRepository(db)
    users = await user_repo.list_admin(
        search=search,
        status=status_filter,
        is_active=is_active,
        is_partner=is_partner,
        offset=offset,
        limit=limit,
    )
    total = await user_repo.count_admin(
        search=search,
        status=status_filter,
        is_active=is_active,
        is_partner=is_partner,
    )
    device_counts = await user_repo.get_device_counts([user.id for user in users])

    route_operations_total.labels(route="admin_mobile_users", action="list", status="success").inc()
    return AdminMobileUsersListResponse(
        items=[
            _serialize_mobile_user_list_item(user, device_counts.get(user.id, 0))
            for user in users
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{user_id}", response_model=AdminMobileUserDetailResponse)
async def get_mobile_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminMobileUserDetailResponse:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id_with_devices(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    route_operations_total.labels(route="admin_mobile_users", action="detail", status="success").inc()
    return _serialize_mobile_user_detail(user)


async def build_mobile_user_subscription_snapshot(
    user: MobileUserModel,
    remnawave_client: RemnawaveClient,
) -> AdminMobileUserSubscriptionSnapshotResponse:
    if not user.remnawave_uuid:
        return AdminMobileUserSubscriptionSnapshotResponse(
            exists=False,
            remnawave_uuid=None,
            subscription_url=user.subscription_url,
            config_error="Customer has no linked VPN user",
        )

    try:
        vpn_uuid = UUID(user.remnawave_uuid)
    except ValueError:
        return AdminMobileUserSubscriptionSnapshotResponse(
            exists=False,
            remnawave_uuid=user.remnawave_uuid,
            subscription_url=user.subscription_url,
            config_error="Invalid Remnawave UUID",
        )

    gateway = RemnawaveUserGateway(client=remnawave_client)
    vpn_user = await gateway.get_by_uuid(vpn_uuid)

    details: RemnawaveSubscriptionDetailsResponse | None = None
    config_error: str | None = None
    try:
        details = await remnawave_client.get_validated(
            f"/subscriptions/by-uuid/{vpn_uuid}",
            RemnawaveSubscriptionDetailsResponse,
        )
    except HTTPStatusError as exc:
        if exc.response.status_code != status.HTTP_404_NOT_FOUND:
            raise
        config_error = "Subscription snapshot not found"
    except Exception:
        config_error = "Subscription snapshot unavailable"

    links = details.links if details is not None else []
    ss_conf_links = details.ss_conf_links if details is not None else {}
    subscription_url = (
        details.subscription_url
        if details is not None and details.subscription_url
        else vpn_user.subscription_url if vpn_user is not None else user.subscription_url
    )
    config = _select_primary_subscription_config(
        links=links,
        subscription_url=subscription_url,
    )
    if config is None and config_error is None:
        config_error = "Subscription config unavailable"

    expires_at = vpn_user.expire_at if vpn_user is not None else (
        details.user.expires_at if details is not None and details.user is not None else None
    )

    return AdminMobileUserSubscriptionSnapshotResponse(
        exists=vpn_user is not None or (details is not None and details.is_found),
        remnawave_uuid=user.remnawave_uuid,
        status=vpn_user.status.value if vpn_user is not None else (
            details.user.user_status.lower()
            if details is not None and details.user is not None and details.user.user_status
            else None
        ),
        short_uuid=vpn_user.short_uuid if vpn_user is not None else (
            details.user.short_uuid if details is not None and details.user is not None else None
        ),
        subscription_uuid=(
            str(vpn_user.subscription_uuid)
            if vpn_user is not None and vpn_user.subscription_uuid
            else None
        ),
        expires_at=expires_at,
        days_left=(
            details.user.days_left
            if details is not None and details.user is not None
            else _compute_days_left(expires_at)
        ),
        traffic_limit_bytes=vpn_user.traffic_limit_bytes if vpn_user is not None else None,
        used_traffic_bytes=vpn_user.used_traffic_bytes if vpn_user is not None else None,
        download_bytes=vpn_user.download_bytes if vpn_user is not None else None,
        upload_bytes=vpn_user.upload_bytes if vpn_user is not None else None,
        lifetime_used_traffic_bytes=vpn_user.lifetime_used_traffic_bytes if vpn_user is not None else None,
        online_at=vpn_user.online_at if vpn_user is not None else None,
        sub_last_user_agent=vpn_user.sub_last_user_agent if vpn_user is not None else None,
        sub_revoked_at=vpn_user.sub_revoked_at if vpn_user is not None else None,
        last_traffic_reset_at=vpn_user.last_traffic_reset_at if vpn_user is not None else None,
        hwid_device_limit=vpn_user.hwid_device_limit if vpn_user is not None else None,
        subscription_url=subscription_url,
        config_available=config is not None,
        config=config,
        config_client_type=_detect_config_client_type(config),
        config_error=config_error,
        links=links,
        ss_conf_links=ss_conf_links,
    )


@router.get("/{user_id}/subscription", response_model=AdminMobileUserSubscriptionSnapshotResponse)
async def get_mobile_user_subscription_snapshot(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminMobileUserSubscriptionSnapshotResponse:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id_with_devices(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    snapshot = await build_mobile_user_subscription_snapshot(user, remnawave_client)
    route_operations_total.labels(route="admin_mobile_users", action="subscription_snapshot", status="success").inc()
    return snapshot


@router.patch("/{user_id}", response_model=AdminMobileUserDetailResponse)
async def update_mobile_user(
    user_id: UUID,
    body: AdminUpdateMobileUserRequest,
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_UPDATE)),
) -> AdminMobileUserDetailResponse:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id_with_devices(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    changed_fields: list[str] = []
    provided_fields = body.model_fields_set

    if "email" in provided_fields:
        normalized_email = _normalize_optional_string(body.email)
        if normalized_email is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email cannot be empty")
        normalized_email = normalized_email.lower()
        existing_user = await user_repo.get_by_email(normalized_email)
        if existing_user is not None and existing_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already in use")
        if user.email != normalized_email:
            user.email = normalized_email
            changed_fields.append("email")

    if "username" in provided_fields:
        normalized_username = _normalize_optional_string(body.username)
        if normalized_username is not None:
            existing_user = await user_repo.get_by_username(normalized_username)
            if existing_user is not None and existing_user.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already in use")
        if user.username != normalized_username:
            user.username = normalized_username
            changed_fields.append("username")

    if "telegram_id" in provided_fields:
        if body.telegram_id is not None:
            existing_user = await user_repo.get_by_telegram_id(body.telegram_id)
            if existing_user is not None and existing_user.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Telegram ID is already linked")
        if user.telegram_id != body.telegram_id:
            user.telegram_id = body.telegram_id
            changed_fields.append("telegram_id")

    if "telegram_username" in provided_fields:
        normalized_telegram_username = _normalize_optional_string(body.telegram_username)
        if normalized_telegram_username is not None:
            normalized_telegram_username = normalized_telegram_username.lstrip("@")
        if user.telegram_username != normalized_telegram_username:
            user.telegram_username = normalized_telegram_username
            changed_fields.append("telegram_username")

    if "referral_code" in provided_fields:
        normalized_referral_code = _normalize_optional_string(body.referral_code)
        if normalized_referral_code is not None:
            normalized_referral_code = normalized_referral_code.upper()
            existing_user = await user_repo.get_by_referral_code(normalized_referral_code)
            if existing_user is not None and existing_user.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Referral code is already in use")
        if user.referral_code != normalized_referral_code:
            user.referral_code = normalized_referral_code
            changed_fields.append("referral_code")

    if "status" in provided_fields and body.status is not None and user.status != body.status:
        user.status = body.status
        changed_fields.append("status")
    if "is_active" in provided_fields and body.is_active is not None and user.is_active != body.is_active:
        user.is_active = body.is_active
        changed_fields.append("is_active")

    if not changed_fields:
        route_operations_total.labels(route="admin_mobile_users", action="update", status="noop").inc()
        return _serialize_mobile_user_detail(user)

    updated_user = await user_repo.update(user)

    await _write_audit_entry(
        db=db,
        action="customer_profile_updated",
        user_id=user_id,
        actor=current_user,
        request=request,
        details={
            "fields": changed_fields,
            "fields_csv": ", ".join(changed_fields),
            "field_count": len(changed_fields),
        },
    )

    route_operations_total.labels(route="admin_mobile_users", action="update", status="success").inc()
    return _serialize_mobile_user_detail(updated_user)
