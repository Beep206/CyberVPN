"""Invite code API routes.

Provides:
- ``POST /invites/redeem``        -- mobile user redeems an invite code
- ``GET  /invites/my``            -- mobile user lists their invite codes
- ``POST /admin/invite-codes``    -- admin creates invite codes
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.services.config_service import ConfigService
from src.application.use_cases.growth_notifications.fanout import PlanCustomerGrowthNotificationFanoutUseCase
from src.application.use_cases.invites.admin_create_invite import AdminCreateInviteUseCase
from src.application.use_cases.invites.redeem_invite import RedeemInviteUseCase
from src.application.use_cases.trial.stage1_trial_provisioning import (
    Stage1TrialProvisioningGateway,
    Stage1TrialProvisioningService,
)
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.domain.exceptions import (
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    InviteCodeNotFoundError,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.growth_benefit_model import InviteBatchModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    ADMIN_GROWTH_SURFACE,
    CUSTOMER_REDEEM_SURFACE,
    log_growth_code_event,
    observe_growth_admin_grant,
    observe_growth_code_issue,
)
from src.infrastructure.monitoring.instrumentation.routes import track_invite_operation
from src.infrastructure.remnawave.client import RemnawaveClient, get_remnawave_client
from src.infrastructure.remnawave.stage1_trial_gateway import RemnawaveStage1TrialProvisioningGateway
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AdminCreateInviteRequest,
    AdminExtendInviteBatchRequest,
    AdminInviteBatchActionRequest,
    AdminInviteBatchDetailResponse,
    AdminInviteBatchExportCodeResponse,
    AdminInviteBatchExportResponse,
    AdminInviteBatchListResponse,
    AdminInviteBatchResponse,
    AdminInviteCodeSummaryResponse,
    CustomerInviteBatchGroupResponse,
    CustomerInviteBatchListResponse,
    CustomerInviteBatchResponse,
    InviteCodeResponse,
    RedeemInviteRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["invites"])


async def _get_stage1_invite_provisioning_gateway(
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> Stage1TrialProvisioningGateway | None:
    if not settings.stage1_trial_provisioning_enabled:
        return None
    return RemnawaveStage1TrialProvisioningGateway(RemnawaveUserGateway(remnawave_client))


async def _provision_redeemed_invite_access(
    *,
    db: AsyncSession,
    user_id: UUID,
    result,
    provisioning_gateway: Stage1TrialProvisioningGateway | None,
) -> None:
    if provisioning_gateway is None:
        return

    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    grant = await db.get(EntitlementGrantModel, result.entitlement_grant_id)
    access_expires_at = grant.expires_at if grant is not None and grant.expires_at is not None else None
    if access_expires_at is None:
        access_expires_at = datetime.now(UTC) + timedelta(days=int(result.invite.free_days))

    provisioning = await Stage1TrialProvisioningService(provisioning_gateway).provision(
        customer_account_id=user_id,
        email=user.email,
        username=user.username,
        telegram_id=user.telegram_id,
        trial_expires_at=access_expires_at,
        existing_remnawave_uuid=user.remnawave_uuid,
    )
    user.remnawave_uuid = provisioning.remnawave_uuid
    user.subscription_url = provisioning.subscription_url
    await user_repo.update(user)


@router.post(
    "/redeem",
    response_model=InviteCodeResponse,
    summary="Redeem an invite code",
    responses={
        404: {"description": "Invite code not found"},
        409: {"description": "Invite code already used"},
        410: {"description": "Invite code expired"},
    },
)
async def redeem_invite(
    body: RedeemInviteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    provisioning_gateway: Stage1TrialProvisioningGateway | None = Depends(_get_stage1_invite_provisioning_gateway),
) -> InviteCodeResponse:
    """Redeem an invite code for the authenticated mobile user."""
    use_case = RedeemInviteUseCase(db)

    try:
        result = await use_case.execute(code=body.code, user_id=user_id, current_realm=current_realm)
    except InviteCodeNotFoundError:
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code not found") from None
    except InviteCodeAlreadyUsedError:
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite code already used") from None
    except InviteCodeExpiredError:
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite code expired") from None
    except ValueError as exc:
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        await _provision_redeemed_invite_access(
            db=db,
            user_id=user_id,
            result=result,
            provisioning_gateway=provisioning_gateway,
        )
    except HTTPException:
        track_invite_operation(operation="redeem", success=False)
        raise
    except Exception as exc:
        track_invite_operation(operation="redeem", success=False)
        logger.exception(
            "invite_vpn_provisioning_failed",
            extra={
                "user_id": str(user_id),
                "invite_id": str(result.invite.id),
                "entitlement_grant_id": str(result.entitlement_grant_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="VPN access provisioning failed",
        ) from exc

    track_invite_operation(operation="redeem", success=True)
    await EventOutboxService(db).append_event(
        event_name="invite.redeemed",
        aggregate_type="invite_code",
        aggregate_id=str(result.invite.id),
        partition_key=str(result.invite.owner_user_id),
        event_payload={
            "invite_code_id": str(result.invite.id),
            "owner_user_id": str(result.invite.owner_user_id),
            "redeemer_user_id": str(user_id),
            "free_days": result.invite.free_days,
            "source": str(result.invite.source),
            "entitlement_grant_id": str(result.entitlement_grant_id),
            "redemption_id": str(result.redemption.id),
        },
        actor_context=OutboxActorContext(
            principal_type="customer",
            principal_id=str(user_id),
            auth_realm_id=str(current_realm.realm_id),
        ),
        source_context={"source_use_case": "redeem_invite_route"},
    )
    log_growth_code_event(
        "invite.redeemed",
        surface=CUSTOMER_REDEEM_SURFACE,
        code_type="invite",
        action_context="redeem",
        result="success",
        invite_code_id=str(result.invite.id),
        owner_user_id=str(result.invite.owner_user_id),
        redeemer_user_id=str(user_id),
        entitlement_grant_id=str(result.entitlement_grant_id),
        redemption_id=str(result.redemption.id),
    )
    return InviteCodeResponse.model_validate(result.invite).model_copy(
        update={
            "entitlement_grant_id": result.entitlement_grant_id,
            "entitlement_snapshot": result.entitlement_snapshot,
        }
    )


@router.get(
    "/my",
    response_model=list[InviteCodeResponse] | CustomerInviteBatchListResponse,
    summary="List my invite codes",
)
async def list_my_invites(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    group_by: str | None = Query(None, description="Use 'batch' to group Growth Codes v6 invite batches"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> list[InviteCodeResponse] | CustomerInviteBatchListResponse:
    """List invite codes owned by the authenticated mobile user."""
    repo = InviteCodeRepository(db)
    invites = await repo.get_by_owner(owner_user_id=user_id, offset=offset, limit=limit)
    track_invite_operation(operation="list", success=True)
    if group_by == "batch":
        return await _serialize_customer_invite_batches(
            db=db,
            owner_user_id=user_id,
            invites=invites,
            offset=offset,
            limit=limit,
        )
    if group_by is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported invite grouping")
    return [InviteCodeResponse.model_validate(inv) for inv in invites]


admin_router = APIRouter(prefix="/admin/invite-codes", tags=["invites"])
invite_batch_admin_router = APIRouter(prefix="/admin/invite-batches", tags=["admin", "invite-batches"])


@admin_router.post(
    "",
    response_model=list[InviteCodeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create invite codes",
)
async def admin_create_invites(
    body: AdminCreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> list[InviteCodeResponse]:
    """Create one or more invite codes (admin only)."""
    invite_repo = InviteCodeRepository(db)
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    use_case = AdminCreateInviteUseCase(
        invite_repo=invite_repo,
        config_service=config_service,
        notification_fanout=PlanCustomerGrowthNotificationFanoutUseCase(db),
    )

    created = await use_case.execute(
        owner_user_id=body.user_id,
        free_days=body.free_days,
        count=body.count,
        plan_id=body.plan_id,
    )
    outbox = EventOutboxService(db)
    for invite in created:
        await outbox.append_event(
            event_name="growth_code.issued",
            aggregate_type="invite_code",
            aggregate_id=str(invite.id),
            partition_key=str(invite.owner_user_id),
            event_payload={
                "invite_code_id": str(invite.id),
                "owner_user_id": str(invite.owner_user_id),
                "free_days": invite.free_days,
                "source": str(invite.source),
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(current_user.id)),
            source_context={"source_use_case": "admin_create_invites_route"},
        )
        observe_growth_code_issue(
            code_type="invite",
            issuer_type="admin",
            surface=ADMIN_GROWTH_SURFACE,
            result="success",
            source_type=str(invite.source),
        )
    observe_growth_admin_grant(
        code_type="invite",
        admin_action_type="batch_issue",
        reason_code="admin_manual_grant",
        result="success",
    )
    log_growth_code_event(
        "admin_growth.invites_issued",
        surface=ADMIN_GROWTH_SURFACE,
        code_type="invite",
        result="success",
        admin_action_type="batch_issue",
        owner_user_id=str(body.user_id),
        issued_count=len(created),
    )

    track_invite_operation(operation="create", success=True)
    return [InviteCodeResponse.model_validate(inv) for inv in created]


@invite_batch_admin_router.get(
    "",
    response_model=AdminInviteBatchListResponse,
    summary="Admin: list invite batches",
)
async def admin_list_invite_batches(
    status_filter: str | None = Query(None, alias="status"),
    owner_user_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminInviteBatchListResponse:
    filters = []
    if status_filter:
        filters.append(InviteBatchModel.status == status_filter)
    if owner_user_id is not None:
        filters.append(InviteBatchModel.owner_user_id == owner_user_id)

    total_result = await db.execute(select(func.count()).select_from(InviteBatchModel).where(*filters))
    total = int(total_result.scalar_one())
    result = await db.execute(
        select(InviteBatchModel)
        .where(*filters)
        .order_by(InviteBatchModel.created_at.desc(), InviteBatchModel.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [AdminInviteBatchResponse.model_validate(batch) for batch in result.scalars().all()]
    return AdminInviteBatchListResponse(items=items, total=total, offset=offset, limit=limit)


@invite_batch_admin_router.get(
    "/{batch_id}",
    response_model=AdminInviteBatchDetailResponse,
    summary="Admin: get invite batch detail",
)
async def admin_get_invite_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminInviteBatchDetailResponse:
    batch = await _get_invite_batch_or_404(db, batch_id)
    return await _serialize_admin_invite_batch_detail(db, batch)


@invite_batch_admin_router.post(
    "/{batch_id}/revoke",
    response_model=AdminInviteBatchDetailResponse,
    summary="Admin: revoke unused invite codes in a batch",
)
async def admin_revoke_invite_batch(
    batch_id: UUID,
    body: AdminInviteBatchActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminInviteBatchDetailResponse:
    batch = await _get_invite_batch_or_404(db, batch_id)
    before = _batch_audit_snapshot(batch)
    now = datetime.now(UTC)
    batch.status = "revoked"
    batch.revoked_at = batch.revoked_at or now
    batch.revoked_by_admin_id = current_user.id
    batch.revoked_reason = body.reason

    invite_result = await db.execute(
        select(InviteCodeModel).where(
            InviteCodeModel.batch_id == batch.id,
            InviteCodeModel.is_used.is_(False),
            InviteCodeModel.revoked_at.is_(None),
        )
    )
    revoked_count = 0
    for invite in invite_result.scalars().all():
        invite.status = "revoked"
        invite.revoked_at = now
        invite.revoked_by_admin_id = current_user.id
        invite.revoked_reason = body.reason
        revoked_count += 1
    await db.flush()
    await _write_invite_batch_admin_audit(
        db=db,
        request=request,
        current_user=current_user,
        action="invite_batch.revoked",
        batch=batch,
        reason=body.reason,
        before=before,
        extra={"revoked_unused_codes": revoked_count},
    )
    await _append_invite_batch_event(
        db=db,
        event_name="invite.batch.revoked",
        batch=batch,
        current_user=current_user,
        payload_extra={"revoked_unused_codes": revoked_count},
    )
    return await _serialize_admin_invite_batch_detail(db, batch)


@invite_batch_admin_router.post(
    "/{batch_id}/extend",
    response_model=AdminInviteBatchDetailResponse,
    summary="Admin: extend unused invite codes in a batch",
)
async def admin_extend_invite_batch(
    batch_id: UUID,
    body: AdminExtendInviteBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminInviteBatchDetailResponse:
    batch = await _get_invite_batch_or_404(db, batch_id)
    before = _batch_audit_snapshot(batch)
    now = datetime.now(UTC)
    if body.expires_at is not None:
        new_expires_at = (
            body.expires_at.astimezone(UTC) if body.expires_at.tzinfo else body.expires_at.replace(tzinfo=UTC)
        )
        batch.expiry_mode = "absolute"
        batch.expiry_days = None
    else:
        base = batch.expires_at if batch.expires_at and batch.expires_at > now else now
        new_expires_at = base + timedelta(days=int(body.expiry_days or 0))
        batch.expiry_mode = "relative"
        batch.expiry_days = int(body.expiry_days or 0)
    batch.expires_at = new_expires_at
    batch.status = "issued" if batch.status != "revoked" else batch.status

    invite_result = await db.execute(
        select(InviteCodeModel).where(
            InviteCodeModel.batch_id == batch.id,
            InviteCodeModel.is_used.is_(False),
            InviteCodeModel.revoked_at.is_(None),
        )
    )
    extended_count = 0
    for invite in invite_result.scalars().all():
        invite.expires_at = new_expires_at
        extended_count += 1
    await db.flush()
    await _write_invite_batch_admin_audit(
        db=db,
        request=request,
        current_user=current_user,
        action="invite_batch.extended",
        batch=batch,
        reason=body.reason,
        before=before,
        extra={"extended_unused_codes": extended_count, "expires_at": new_expires_at.isoformat()},
    )
    await _append_invite_batch_event(
        db=db,
        event_name="invite.batch.extended",
        batch=batch,
        current_user=current_user,
        payload_extra={"extended_unused_codes": extended_count, "expires_at": new_expires_at.isoformat()},
    )
    return await _serialize_admin_invite_batch_detail(db, batch)


@invite_batch_admin_router.post(
    "/{batch_id}/resend",
    response_model=AdminInviteBatchDetailResponse,
    summary="Admin: request resend of invite batch notification",
)
async def admin_resend_invite_batch(
    batch_id: UUID,
    body: AdminInviteBatchActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminInviteBatchDetailResponse:
    batch = await _get_invite_batch_or_404(db, batch_id)
    await _write_invite_batch_admin_audit(
        db=db,
        request=request,
        current_user=current_user,
        action="invite_batch.resend_requested",
        batch=batch,
        reason=body.reason,
        before=_batch_audit_snapshot(batch),
        extra={"requested": True},
    )
    await _append_invite_batch_event(
        db=db,
        event_name="invite.batch.resend_requested",
        batch=batch,
        current_user=current_user,
        payload_extra={"reason": body.reason},
    )
    return await _serialize_admin_invite_batch_detail(db, batch)


@invite_batch_admin_router.get(
    "/{batch_id}/export",
    response_model=AdminInviteBatchExportResponse,
    summary="Admin: export raw invite codes for a batch",
)
async def admin_export_invite_batch(
    batch_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AdminInviteBatchExportResponse:
    batch = await _get_invite_batch_or_404(db, batch_id)
    invites = await _list_invite_codes_for_batch(db, batch.id)
    await _write_invite_batch_admin_audit(
        db=db,
        request=request,
        current_user=current_user,
        action="invite_batch.exported",
        batch=batch,
        reason="explicit_export",
        before=_batch_audit_snapshot(batch),
        extra={"exported_count": len(invites)},
    )
    return AdminInviteBatchExportResponse(
        batch_id=batch.id,
        exported_count=len(invites),
        codes=[
            AdminInviteBatchExportCodeResponse(
                id=invite.id,
                code=invite.code,
                code_prefix=invite.code_prefix,
                code_hash=invite.code_hash,
                status=invite.status,
                is_used=invite.is_used,
                expires_at=invite.expires_at,
            )
            for invite in invites
        ],
    )


async def _serialize_customer_invite_batches(
    *,
    db: AsyncSession,
    owner_user_id: UUID,
    invites: list[InviteCodeModel],
    offset: int,
    limit: int,
) -> CustomerInviteBatchListResponse:
    batch_ids = {invite.batch_id for invite in invites if invite.batch_id is not None}
    batches: dict[UUID, InviteBatchModel] = {}
    if batch_ids:
        result = await db.execute(
            select(InviteBatchModel).where(
                InviteBatchModel.id.in_(batch_ids),
                InviteBatchModel.owner_user_id == owner_user_id,
            )
        )
        batches = {batch.id: batch for batch in result.scalars().all()}

    invites_by_batch: dict[UUID, list[InviteCodeResponse]] = {batch_id: [] for batch_id in batches}
    unbatched: list[InviteCodeResponse] = []
    for invite in invites:
        serialized = InviteCodeResponse.model_validate(invite)
        if invite.batch_id is not None and invite.batch_id in invites_by_batch:
            invites_by_batch[invite.batch_id].append(serialized)
        else:
            unbatched.append(serialized)

    groups = [
        CustomerInviteBatchGroupResponse(
            batch=CustomerInviteBatchResponse.model_validate(batch),
            invites=invites_by_batch[batch.id],
        )
        for batch in sorted(batches.values(), key=lambda item: (item.created_at, item.id), reverse=True)
    ]
    return CustomerInviteBatchListResponse(
        batches=groups,
        unbatched=unbatched,
        total_batches=len(groups),
        total_invites=len(invites),
        offset=offset,
        limit=limit,
    )


async def _get_invite_batch_or_404(db: AsyncSession, batch_id: UUID) -> InviteBatchModel:
    batch = await db.get(InviteBatchModel, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite batch not found")
    return batch


async def _list_invite_codes_for_batch(db: AsyncSession, batch_id: UUID) -> list[InviteCodeModel]:
    result = await db.execute(
        select(InviteCodeModel).where(InviteCodeModel.batch_id == batch_id).order_by(InviteCodeModel.created_at.asc())
    )
    return list(result.scalars().all())


async def _serialize_admin_invite_batch_detail(
    db: AsyncSession,
    batch: InviteBatchModel,
) -> AdminInviteBatchDetailResponse:
    invites = await _list_invite_codes_for_batch(db, batch.id)
    payload = AdminInviteBatchResponse.model_validate(batch).model_dump()
    return AdminInviteBatchDetailResponse(
        **payload,
        invites=[
            AdminInviteCodeSummaryResponse(
                id=invite.id,
                code_prefix=invite.code_prefix,
                code_hash=invite.code_hash,
                status=invite.status,
                is_used=invite.is_used,
                used_by_user_id=invite.used_by_user_id,
                used_at=invite.used_at,
                revoked_at=invite.revoked_at,
                expires_at=invite.expires_at,
                created_at=invite.created_at,
            )
            for invite in invites
        ],
    )


def _batch_audit_snapshot(batch: InviteBatchModel) -> dict[str, object]:
    return {
        "id": str(batch.id),
        "owner_user_id": str(batch.owner_user_id),
        "status": batch.status,
        "requested_count": batch.requested_count,
        "issued_count": batch.issued_count,
        "expires_at": batch.expires_at.isoformat() if batch.expires_at else None,
        "revoked_at": batch.revoked_at.isoformat() if batch.revoked_at else None,
    }


async def _write_invite_batch_admin_audit(
    *,
    db: AsyncSession,
    request: Request,
    current_user: AdminUserModel,
    action: str,
    batch: InviteBatchModel,
    reason: str,
    before: dict[str, object],
    extra: dict[str, object],
) -> None:
    await write_required_admin_audit_entry(
        db=db,
        action=action,
        resource_type="invite_batch",
        resource_id=batch.id,
        actor=current_user,
        request=request,
        old_value=before,
        details={
            **_batch_audit_snapshot(batch),
            **extra,
            "reason": reason,
        },
    )


async def _append_invite_batch_event(
    *,
    db: AsyncSession,
    event_name: str,
    batch: InviteBatchModel,
    current_user: AdminUserModel,
    payload_extra: dict[str, object],
) -> None:
    await EventOutboxService(db).append_event(
        event_name=event_name,
        aggregate_type="invite_batch",
        aggregate_id=str(batch.id),
        partition_key=str(batch.owner_user_id),
        event_payload={
            "invite_batch_id": str(batch.id),
            "owner_user_id": str(batch.owner_user_id),
            "status": batch.status,
            "requested_count": batch.requested_count,
            "issued_count": batch.issued_count,
            **payload_extra,
        },
        actor_context=OutboxActorContext(principal_type="admin", principal_id=str(current_user.id)),
        source_context={"source_use_case": "admin_invite_batch_route"},
    )
