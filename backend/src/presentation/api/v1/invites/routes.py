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
from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.growth_notifications.fanout import PlanCustomerGrowthNotificationFanoutUseCase
from src.application.use_cases.invites.admin_create_invite import AdminCreateInviteUseCase
from src.application.use_cases.invites.campaigns import (
    CreateInviteCampaignBatchCommand,
    CreateInviteCampaignBatchUseCase,
    CreateInviteCampaignCommand,
    CreateInviteCampaignUseCase,
    CreateInviteCampaignVersionCommand,
    CreateInviteCampaignVersionUseCase,
    PublishInviteCampaignVersionUseCase,
    ValidateInviteCampaignVersionUseCase,
    list_invite_campaigns,
)
from src.application.use_cases.invites.redeem_invite import RedeemInviteUseCase
from src.application.use_cases.service_access.entitlements import RevokeEntitlementGrantUseCase
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
from src.infrastructure.database.models.invite_campaign_model import (
    InviteCampaignModel,
    InviteCampaignVersionModel,
    InviteRedemptionModel,
    InviteTreeEdgeModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
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
from src.presentation.dependencies.roles import require_permission

from .schemas import (
    AdminCreateInviteRequest,
    AdminExtendInviteBatchRequest,
    AdminInviteBatchActionRequest,
    AdminInviteBatchDetailResponse,
    AdminInviteBatchExportCodeResponse,
    AdminInviteBatchExportResponse,
    AdminInviteBatchListResponse,
    AdminInviteBatchResponse,
    AdminInviteCampaignActionRequest,
    AdminInviteCampaignBatchCreateRequest,
    AdminInviteCampaignBatchCreateResponse,
    AdminInviteCampaignCreateRequest,
    AdminInviteCampaignListResponse,
    AdminInviteCampaignResponse,
    AdminInviteCampaignVersionCreateRequest,
    AdminInviteCampaignVersionResponse,
    AdminInviteCampaignVersionValidationResponse,
    AdminInviteCodeSummaryResponse,
    AdminInviteRedemptionListResponse,
    AdminInviteRedemptionResponse,
    AdminInviteTreeEdgeResponse,
    AdminInviteTreeNodeResponse,
    AdminInviteTreeResponse,
    AdminInviteTreeRootListResponse,
    AdminInviteTreeRootResponse,
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
    if _invite_result_is_plan_backed(result):
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
        result = await use_case.execute(
            code=body.code,
            user_id=user_id,
            current_realm=current_realm,
            source_surface="web",
        )
    except InviteCodeNotFoundError:
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code not found") from None
    except InviteCodeAlreadyUsedError:
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite code already used") from None
    except InviteCodeExpiredError:
        await db.commit()
        track_invite_operation(operation="redeem", success=False)
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite code expired") from None
    except ValueError as exc:
        await db.commit()
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
            "invite_redemption_id": str(result.invite_redemption.id) if result.invite_redemption else None,
            "child_batch_id": str(result.child_batch.id) if result.child_batch else None,
            "child_invite_count": len(result.child_invites),
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
        invite_redemption_id=str(result.invite_redemption.id) if result.invite_redemption else None,
        child_invite_count=len(result.child_invites),
    )
    return InviteCodeResponse.model_validate(result.invite).model_copy(
        update={
            "entitlement_grant_id": result.entitlement_grant_id,
            "entitlement_snapshot": result.entitlement_snapshot,
        }
    )


def _invite_result_is_plan_backed(result) -> bool:
    snapshot = dict(getattr(result, "entitlement_snapshot", {}) or {})
    plan_code = snapshot.get("plan_code")
    if isinstance(plan_code, str) and plan_code not in {"", "invite", "trial"}:
        return True
    invite = getattr(result, "invite", None)
    return bool(invite is not None and getattr(invite, "grant_mode", None) in {"plan_snapshot", "custom_snapshot"})


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
invite_campaign_admin_router = APIRouter(prefix="/admin/invite-campaigns", tags=["admin", "invite-campaigns"])
invite_redemption_admin_router = APIRouter(prefix="/admin/invite-redemptions", tags=["admin", "invite-redemptions"])
invite_tree_admin_router = APIRouter(prefix="/admin/invite-trees", tags=["admin", "invite-trees"])


@admin_router.post(
    "",
    response_model=list[InviteCodeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create invite codes",
)
async def admin_create_invites(
    body: AdminCreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MANAGE_INVITES)),
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


@admin_router.get(
    "",
    response_model=list[AdminInviteCodeSummaryResponse],
    summary="Admin: list invite code inventory",
)
async def admin_list_invite_codes(
    campaign_id: UUID | None = Query(None),
    campaign_key: str | None = Query(None, min_length=1, max_length=80),
    batch_id: UUID | None = Query(None),
    owner_user_id: UUID | None = Query(None),
    used_by_user_id: UUID | None = Query(None),
    root_invite_code_id: UUID | None = Query(None),
    parent_invite_code_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    used: bool | None = Query(None),
    plan_id: UUID | None = Query(None),
    plan_code: str | None = Query(None, min_length=1, max_length=80),
    generation_depth: int | None = Query(None, ge=0),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    used_from: datetime | None = Query(None),
    used_to: datetime | None = Query(None),
    expires_from: datetime | None = Query(None),
    expires_to: datetime | None = Query(None),
    prefix: str | None = Query(None, min_length=1, max_length=12),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> list[AdminInviteCodeSummaryResponse]:
    filters = []
    if campaign_id is not None:
        filters.append(InviteCodeModel.campaign_id == campaign_id)
    if campaign_key:
        campaign_id_result = await db.execute(
            select(InviteCampaignModel.id).where(InviteCampaignModel.campaign_key == campaign_key)
        )
        campaign_ids = list(campaign_id_result.scalars().all())
        filters.append(InviteCodeModel.campaign_id.in_(campaign_ids or [UUID("00000000-0000-0000-0000-000000000000")]))
    if batch_id is not None:
        filters.append(InviteCodeModel.batch_id == batch_id)
    if owner_user_id is not None:
        filters.append(InviteCodeModel.owner_user_id == owner_user_id)
    if used_by_user_id is not None:
        filters.append(InviteCodeModel.used_by_user_id == used_by_user_id)
    if root_invite_code_id is not None:
        filters.append(InviteCodeModel.root_invite_code_id == root_invite_code_id)
    if parent_invite_code_id is not None:
        filters.append(InviteCodeModel.parent_invite_code_id == parent_invite_code_id)
    if status_filter:
        filters.append(InviteCodeModel.status == status_filter)
    if used is not None:
        filters.append(InviteCodeModel.is_used.is_(used))
    if plan_id is not None:
        filters.append((InviteCodeModel.grant_plan_id == plan_id) | (InviteCodeModel.plan_id == plan_id))
    if plan_code:
        plan_id_result = await db.execute(
            select(SubscriptionPlanModel.id).where(SubscriptionPlanModel.plan_code == plan_code)
        )
        plan_ids = list(plan_id_result.scalars().all())
        filters.append(
            (InviteCodeModel.grant_plan_id.in_(plan_ids)) | (InviteCodeModel.plan_id.in_(plan_ids))
            if plan_ids
            else InviteCodeModel.id.is_(None)
        )
    if generation_depth is not None:
        filters.append(InviteCodeModel.generation_depth == generation_depth)
    if created_from is not None:
        filters.append(InviteCodeModel.created_at >= created_from)
    if created_to is not None:
        filters.append(InviteCodeModel.created_at <= created_to)
    if used_from is not None:
        filters.append(InviteCodeModel.used_at >= used_from)
    if used_to is not None:
        filters.append(InviteCodeModel.used_at <= used_to)
    if expires_from is not None:
        filters.append(InviteCodeModel.expires_at >= expires_from)
    if expires_to is not None:
        filters.append(InviteCodeModel.expires_at <= expires_to)
    if prefix:
        filters.append(InviteCodeModel.code_prefix == prefix.upper())

    result = await db.execute(
        select(InviteCodeModel)
        .where(*filters)
        .order_by(InviteCodeModel.created_at.desc(), InviteCodeModel.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_serialize_admin_invite_code(invite) for invite in result.scalars().all()]


@invite_campaign_admin_router.get(
    "",
    response_model=AdminInviteCampaignListResponse,
    summary="Admin: list flexible invite campaigns",
)
async def admin_list_invite_campaigns(
    status_filter: str | None = Query(None, alias="status"),
    campaign_key: str | None = Query(None, min_length=1, max_length=80),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> AdminInviteCampaignListResponse:
    items, total = await list_invite_campaigns(
        db,
        status=status_filter,
        campaign_key=campaign_key,
        offset=offset,
        limit=limit,
    )
    return AdminInviteCampaignListResponse(
        items=[await _serialize_invite_campaign(db, item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@invite_campaign_admin_router.post(
    "",
    response_model=AdminInviteCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create flexible invite campaign",
)
async def admin_create_invite_campaign(
    body: AdminInviteCampaignCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
) -> AdminInviteCampaignResponse:
    try:
        campaign = await CreateInviteCampaignUseCase(db).execute(
            command=CreateInviteCampaignCommand(
                campaign_key=body.campaign_key,
                name=body.name,
                description=body.description,
                owner_mode=body.owner_mode,
                starts_at=body.starts_at,
                expires_at=body.expires_at,
                allowed_surfaces=body.allowed_surfaces,
                allowed_geos=body.allowed_geos,
                allowed_markets=body.allowed_markets,
                allowed_segments=body.allowed_segments,
                risk_policy_key=body.risk_policy_key,
                grant_plan_id=body.grant_plan_id,
                grant_plan_code=body.grant_plan_code,
                grant_duration_days=body.grant_duration_days,
                child_grant_plan_id=body.child_grant_plan_id,
                child_grant_plan_code=body.child_grant_plan_code,
                child_grant_duration_days=body.child_grant_duration_days,
                child_invite_count=body.child_invite_count,
                child_invite_free_days=body.child_invite_free_days,
                child_invite_expiry_days=body.child_invite_expiry_days,
                max_generation_depth=body.max_generation_depth,
                require_no_active_access=body.require_no_active_access,
                block_self_redemption=body.block_self_redemption,
                risk_policy=body.risk_policy,
                export_policy=body.export_policy,
                notification_policy=body.notification_policy,
                caps=body.caps,
                publish=body.publish,
                reason=body.reason,
            ),
            admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return await _serialize_invite_campaign(db, campaign)


@invite_campaign_admin_router.get(
    "/{campaign_id}",
    response_model=AdminInviteCampaignResponse,
    summary="Admin: get flexible invite campaign",
)
async def admin_get_invite_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> AdminInviteCampaignResponse:
    campaign = await _get_invite_campaign_or_404(db, campaign_id)
    return await _serialize_invite_campaign(db, campaign)


@invite_campaign_admin_router.post(
    "/{campaign_id}/versions",
    response_model=AdminInviteCampaignVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create draft invite campaign version",
)
async def admin_create_invite_campaign_version(
    campaign_id: UUID,
    body: AdminInviteCampaignVersionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
) -> AdminInviteCampaignVersionResponse:
    try:
        version = await CreateInviteCampaignVersionUseCase(db).execute(
            campaign_id=campaign_id,
            command=CreateInviteCampaignVersionCommand(
                grant_plan_id=body.grant_plan_id,
                grant_plan_code=body.grant_plan_code,
                grant_duration_days=body.grant_duration_days,
                child_invite_count=body.child_invite_count,
                child_invite_free_days=body.child_invite_free_days,
                child_invite_expiry_days=body.child_invite_expiry_days,
                child_grant_plan_id=body.child_grant_plan_id,
                child_grant_plan_code=body.child_grant_plan_code,
                child_grant_duration_days=body.child_grant_duration_days,
                max_generation_depth=body.max_generation_depth,
                require_no_active_access=body.require_no_active_access,
                block_self_redemption=body.block_self_redemption,
                allowed_surfaces=body.allowed_surfaces,
                risk_policy=body.risk_policy,
                export_policy=body.export_policy,
                notification_policy=body.notification_policy,
                reason=body.reason,
            ),
            admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AdminInviteCampaignVersionResponse.model_validate(version)


@invite_campaign_admin_router.post(
    "/{campaign_id}/versions/{version_id}/validate",
    response_model=AdminInviteCampaignVersionValidationResponse,
    summary="Admin: validate invite campaign version before publish",
)
async def admin_validate_invite_campaign_version(
    campaign_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
) -> AdminInviteCampaignVersionValidationResponse:
    try:
        result = await ValidateInviteCampaignVersionUseCase(db).execute(
            campaign_id=campaign_id,
            version_id=version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminInviteCampaignVersionValidationResponse(
        version_id=result.version_id,
        checksum=result.checksum,
        valid=result.valid,
        errors=list(result.errors),
        warnings=list(result.warnings),
    )


@invite_campaign_admin_router.post(
    "/{campaign_id}/versions/{version_id}/publish",
    response_model=AdminInviteCampaignResponse,
    summary="Admin: publish invite campaign version",
)
async def admin_publish_invite_campaign_version(
    campaign_id: UUID,
    version_id: UUID,
    _body: AdminInviteCampaignActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_PUBLISH)),
) -> AdminInviteCampaignResponse:
    try:
        campaign = await PublishInviteCampaignVersionUseCase(db).execute(
            campaign_id=campaign_id,
            version_id=version_id,
            admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return await _serialize_invite_campaign(db, campaign)


@invite_campaign_admin_router.post(
    "/{campaign_id}/pause",
    response_model=AdminInviteCampaignResponse,
    summary="Admin: pause invite campaign",
)
async def admin_pause_invite_campaign(
    campaign_id: UUID,
    _body: AdminInviteCampaignActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_PAUSE)),
) -> AdminInviteCampaignResponse:
    campaign = await _get_invite_campaign_or_404(db, campaign_id)
    campaign.status = "paused"
    campaign.paused_at = datetime.now(UTC)
    campaign.updated_by_admin_id = current_user.id
    await db.flush()
    return await _serialize_invite_campaign(db, campaign)


@invite_campaign_admin_router.post(
    "/{campaign_id}/resume",
    response_model=AdminInviteCampaignResponse,
    summary="Admin: resume invite campaign",
)
async def admin_resume_invite_campaign(
    campaign_id: UUID,
    _body: AdminInviteCampaignActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_PAUSE)),
) -> AdminInviteCampaignResponse:
    campaign = await _get_invite_campaign_or_404(db, campaign_id)
    campaign.status = "active"
    campaign.paused_at = None
    campaign.updated_by_admin_id = current_user.id
    await db.flush()
    return await _serialize_invite_campaign(db, campaign)


@invite_campaign_admin_router.post(
    "/{campaign_id}/archive",
    response_model=AdminInviteCampaignResponse,
    summary="Admin: archive invite campaign",
)
async def admin_archive_invite_campaign(
    campaign_id: UUID,
    _body: AdminInviteCampaignActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_REVOKE)),
) -> AdminInviteCampaignResponse:
    campaign = await _get_invite_campaign_or_404(db, campaign_id)
    campaign.status = "archived"
    campaign.archived_at = datetime.now(UTC)
    campaign.updated_by_admin_id = current_user.id
    await db.flush()
    return await _serialize_invite_campaign(db, campaign)


@invite_campaign_admin_router.post(
    "/{campaign_id}/batches",
    response_model=AdminInviteCampaignBatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create root invite batch for campaign",
)
async def admin_create_invite_campaign_batch(
    campaign_id: UUID,
    body: AdminInviteCampaignBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
) -> AdminInviteCampaignBatchCreateResponse:
    try:
        result = await CreateInviteCampaignBatchUseCase(db).execute(
            command=CreateInviteCampaignBatchCommand(
                campaign_id=campaign_id,
                owner_user_id=body.owner_user_id,
                owner_user_ids=tuple(body.owner_user_ids),
                count=body.count,
                version_id=body.version_id,
                idempotency_key=body.idempotency_key,
                expires_at=body.expires_at,
                expiry_days=body.expiry_days,
                reason=body.reason,
            ),
            admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AdminInviteCampaignBatchCreateResponse(
        campaign=await _serialize_invite_campaign(db, result.campaign),
        batch=AdminInviteBatchResponse.model_validate(result.batch),
        raw_codes=list(result.raw_codes) if await _can_return_raw_codes(db, result.batch, current_user) else [],
    )


@invite_campaign_admin_router.get(
    "/{campaign_id}/redemptions",
    response_model=AdminInviteRedemptionListResponse,
    summary="Admin: list invite redemptions for campaign",
)
async def admin_list_invite_campaign_redemptions(
    campaign_id: UUID,
    status_filter: str | None = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> AdminInviteRedemptionListResponse:
    filters = [InviteRedemptionModel.campaign_id == campaign_id]
    if status_filter:
        filters.append(InviteRedemptionModel.status == status_filter)
    total_result = await db.execute(select(func.count()).select_from(InviteRedemptionModel).where(*filters))
    rows = await db.execute(
        select(InviteRedemptionModel)
        .where(*filters)
        .order_by(InviteRedemptionModel.created_at.desc(), InviteRedemptionModel.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return AdminInviteRedemptionListResponse(
        items=[AdminInviteRedemptionResponse.model_validate(item) for item in rows.scalars().all()],
        total=int(total_result.scalar_one()),
        offset=offset,
        limit=limit,
    )


@invite_campaign_admin_router.get(
    "/{campaign_id}/analytics",
    response_model=dict[str, object],
    summary="Admin: invite campaign analytics",
)
async def admin_get_invite_campaign_analytics(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> dict[str, object]:
    issued = await db.execute(
        select(func.count()).select_from(InviteCodeModel).where(InviteCodeModel.campaign_id == campaign_id)
    )
    redeemed = await db.execute(
        select(func.count())
        .select_from(InviteRedemptionModel)
        .where(
            InviteRedemptionModel.campaign_id == campaign_id,
            InviteRedemptionModel.status == "redeemed",
        )
    )
    blocked = await db.execute(
        select(func.count())
        .select_from(InviteRedemptionModel)
        .where(
            InviteRedemptionModel.campaign_id == campaign_id,
            InviteRedemptionModel.status == "blocked",
        )
    )
    child_batches = await db.execute(
        select(func.coalesce(func.sum(InviteBatchModel.issued_count), 0)).where(
            InviteBatchModel.invite_campaign_id == campaign_id,
            InviteBatchModel.batch_kind == "child_after_redemption",
        )
    )
    max_depth = await db.execute(
        select(func.coalesce(func.max(InviteCodeModel.generation_depth), 0)).where(
            InviteCodeModel.campaign_id == campaign_id
        )
    )
    depth_rows = await db.execute(
        select(InviteCodeModel.generation_depth, func.count())
        .where(InviteCodeModel.campaign_id == campaign_id)
        .group_by(InviteCodeModel.generation_depth)
        .order_by(InviteCodeModel.generation_depth.asc())
    )
    active_vpn = await db.execute(
        select(func.count())
        .select_from(InviteRedemptionModel)
        .join(EntitlementGrantModel, EntitlementGrantModel.id == InviteRedemptionModel.entitlement_grant_id)
        .where(
            InviteRedemptionModel.campaign_id == campaign_id,
            InviteRedemptionModel.status == "redeemed",
            EntitlementGrantModel.grant_status == "active",
            EntitlementGrantModel.revoked_at.is_(None),
            EntitlementGrantModel.suspended_at.is_(None),
        )
    )
    issued_total = int(issued.scalar_one())
    redeemed_total = int(redeemed.scalar_one())
    active_vpn_total = int(active_vpn.scalar_one())
    issued_to_redeemed_pct = round((redeemed_total / issued_total) * 100, 2) if issued_total else 0.0
    redeemed_to_connected_pct = round((active_vpn_total / redeemed_total) * 100, 2) if redeemed_total else 0.0
    return {
        "campaign_id": str(campaign_id),
        "issued_count": issued_total,
        "issued_total": issued_total,
        "redeemed_count": redeemed_total,
        "redeemed_total": redeemed_total,
        "blocked_count": int(blocked.scalar_one()),
        "active_vpn_total": active_vpn_total,
        "child_invites_issued_total": int(child_batches.scalar_one() or 0),
        "max_depth_reached": int(max_depth.scalar_one() or 0),
        "depth_breakdown": {str(depth): int(count) for depth, count in depth_rows.all()},
        "conversion": {
            "issued_to_redeemed_pct": issued_to_redeemed_pct,
            "redeemed_to_connected_pct": redeemed_to_connected_pct,
        },
    }


@invite_redemption_admin_router.post(
    "/{redemption_id}/reverse",
    response_model=AdminInviteRedemptionResponse,
    summary="Admin: reverse invite redemption",
)
async def admin_reverse_invite_redemption(
    redemption_id: UUID,
    body: AdminInviteCampaignActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_REVOKE)),
) -> AdminInviteRedemptionResponse:
    redemption = await db.get(InviteRedemptionModel, redemption_id)
    if redemption is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite redemption not found")
    before = {
        "id": str(redemption.id),
        "status": redemption.status,
        "entitlement_grant_id": str(redemption.entitlement_grant_id) if redemption.entitlement_grant_id else None,
        "child_batch_id": str(redemption.child_batch_id) if redemption.child_batch_id else None,
    }
    if redemption.status != "reversed":
        now = datetime.now(UTC)
        redemption.status = "reversed"
        redemption.reversed_at = now
        redemption.blocked_reason = body.reason
        if redemption.entitlement_grant_id is not None:
            grant = await db.get(EntitlementGrantModel, redemption.entitlement_grant_id)
            if grant is not None and grant.grant_status not in {"revoked", "expired"}:
                await RevokeEntitlementGrantUseCase(db).execute(
                    entitlement_grant_id=grant.id,
                    revoked_by_admin_user_id=current_user.id,
                    reason_code="invite_redemption_reversed",
                )
        if redemption.child_batch_id is not None:
            child_batch = await db.get(InviteBatchModel, redemption.child_batch_id)
            if child_batch is not None:
                child_batch.status = "revoked"
                child_batch.revoked_at = child_batch.revoked_at or now
                child_batch.revoked_by_admin_id = current_user.id
                child_batch.revoked_reason = body.reason
                child_invites = await db.execute(
                    select(InviteCodeModel).where(
                        InviteCodeModel.batch_id == child_batch.id,
                        InviteCodeModel.is_used.is_(False),
                        InviteCodeModel.revoked_at.is_(None),
                    )
                )
                for invite in child_invites.scalars().all():
                    invite.status = "revoked"
                    invite.revoked_at = now
                    invite.revoked_by_admin_id = current_user.id
                    invite.revoked_reason = body.reason
        edge_result = await db.execute(
            select(InviteTreeEdgeModel).where(InviteTreeEdgeModel.redemption_id == redemption.id)
        )
        for edge in edge_result.scalars().all():
            edge.status = "reversed"
        await db.flush()
        await write_required_admin_audit_entry(
            db=db,
            action="invite_redemption.reversed",
            resource_type="invite_redemption",
            resource_id=redemption.id,
            actor=current_user,
            request=request,
            old_value=before,
            details={
                "id": str(redemption.id),
                "status": redemption.status,
                "reason": body.reason,
                "invite_code_id": str(redemption.invite_code_id),
                "invitee_user_id": str(redemption.invitee_user_id),
            },
        )
        await EventOutboxService(db).append_event(
            event_name="invite.redemption.reversed",
            aggregate_type="invite_redemption",
            aggregate_id=str(redemption.id),
            partition_key=str(redemption.invitee_user_id),
            event_payload={
                "invite_redemption_id": str(redemption.id),
                "invite_code_id": str(redemption.invite_code_id),
                "invitee_user_id": str(redemption.invitee_user_id),
                "campaign_id": str(redemption.campaign_id) if redemption.campaign_id else None,
                "entitlement_grant_id": str(redemption.entitlement_grant_id)
                if redemption.entitlement_grant_id
                else None,
                "child_batch_id": str(redemption.child_batch_id) if redemption.child_batch_id else None,
                "reason": body.reason,
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(current_user.id)),
            source_context={"source_use_case": "admin_reverse_invite_redemption_route"},
        )
    return AdminInviteRedemptionResponse.model_validate(redemption)


@invite_tree_admin_router.get(
    "",
    response_model=AdminInviteTreeRootListResponse,
    summary="Admin: list invite tree roots",
)
async def admin_list_invite_tree_roots(
    campaign_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> AdminInviteTreeRootListResponse:
    filters = [
        InviteCodeModel.root_invite_code_id == InviteCodeModel.id,
        InviteCodeModel.generation_depth == 0,
    ]
    if campaign_id is not None:
        filters.append(InviteCodeModel.campaign_id == campaign_id)

    total_result = await db.execute(select(func.count()).select_from(InviteCodeModel).where(*filters))
    root_rows = await db.execute(
        select(InviteCodeModel, InviteCampaignModel.campaign_key)
        .outerjoin(InviteCampaignModel, InviteCampaignModel.id == InviteCodeModel.campaign_id)
        .where(*filters)
        .order_by(InviteCodeModel.created_at.desc(), InviteCodeModel.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items: list[AdminInviteTreeRootResponse] = []
    for invite, campaign_key in root_rows.all():
        stats = await _build_invite_tree_stats(db, invite.root_invite_code_id or invite.id)
        items.append(
            AdminInviteTreeRootResponse(
                root_invite_code_id=invite.root_invite_code_id or invite.id,
                campaign_id=invite.campaign_id,
                campaign_key=campaign_key,
                owner_user_id=invite.owner_user_id,
                generation_depth=int(invite.generation_depth or 0),
                status=invite.status,
                issued_count=int(stats.get("total_nodes", 0)),
                redeemed_count=int(stats.get("total_redeemed", 0)),
                child_invites_issued_count=int(stats.get("total_child_invites_issued", 0)),
                max_depth_reached=int(stats.get("max_depth_reached", 0)),
                created_at=invite.created_at,
            )
        )
    return AdminInviteTreeRootListResponse(
        items=items,
        total=int(total_result.scalar_one()),
        offset=offset,
        limit=limit,
    )


@invite_tree_admin_router.get(
    "/users/{user_id}",
    response_model=AdminInviteTreeResponse,
    summary="Admin: get invite tree for a user",
)
async def admin_get_invite_tree_for_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> AdminInviteTreeResponse:
    invite_result = await db.execute(
        select(InviteCodeModel)
        .where((InviteCodeModel.owner_user_id == user_id) | (InviteCodeModel.used_by_user_id == user_id))
        .order_by(InviteCodeModel.created_at.asc())
        .limit(1)
    )
    invite = invite_result.scalars().first()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite tree was not found")
    return await _build_invite_tree_response(db, invite.root_invite_code_id or invite.id)


@invite_tree_admin_router.get(
    "/{root_invite_code_id}",
    response_model=AdminInviteTreeResponse,
    summary="Admin: get invite tree by root invite code",
)
async def admin_get_invite_tree(
    root_invite_code_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
) -> AdminInviteTreeResponse:
    return await _build_invite_tree_response(db, root_invite_code_id)


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
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
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
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_INSPECT)),
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
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_REVOKE)),
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
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
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
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
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
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CODE_SETS_EXPORT)),
) -> AdminInviteBatchExportResponse:
    batch = await _get_invite_batch_or_404(db, batch_id)
    await _ensure_raw_export_allowed(db, batch)
    invites = await _list_invite_codes_for_batch(db, batch.id)
    now = datetime.now(UTC)
    exportable_invites = [
        invite
        for invite in invites
        if not invite.is_used
        and invite.revoked_at is None
        and invite.status not in {"revoked", "expired"}
        and (_coerce_utc(invite.expires_at) is None or _coerce_utc(invite.expires_at) > now)
    ]
    await _write_invite_batch_admin_audit(
        db=db,
        request=request,
        current_user=current_user,
        action="invite_batch.exported",
        batch=batch,
        reason="explicit_export",
        before=_batch_audit_snapshot(batch),
        extra={"exported_count": len(exportable_invites), "filtered_count": len(invites) - len(exportable_invites)},
    )
    return AdminInviteBatchExportResponse(
        batch_id=batch.id,
        exported_count=len(exportable_invites),
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
            for invite in exportable_invites
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


async def _get_invite_campaign_or_404(db: AsyncSession, campaign_id: UUID) -> InviteCampaignModel:
    campaign = await db.get(InviteCampaignModel, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite campaign not found")
    return campaign


async def _list_invite_codes_for_batch(db: AsyncSession, batch_id: UUID) -> list[InviteCodeModel]:
    result = await db.execute(
        select(InviteCodeModel).where(InviteCodeModel.batch_id == batch_id).order_by(InviteCodeModel.created_at.asc())
    )
    return list(result.scalars().all())


def _serialize_admin_invite_code(invite: InviteCodeModel) -> AdminInviteCodeSummaryResponse:
    return AdminInviteCodeSummaryResponse(
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
        campaign_id=invite.campaign_id,
        campaign_version_id=invite.campaign_version_id,
        root_invite_code_id=invite.root_invite_code_id,
        parent_invite_code_id=invite.parent_invite_code_id,
        generation_depth=invite.generation_depth,
        grant_mode=invite.grant_mode,
        grant_plan_id=invite.grant_plan_id,
        grant_duration_days=invite.grant_duration_days,
        child_grant_plan_id=invite.child_grant_plan_id,
        child_grant_duration_days=invite.child_grant_duration_days,
    )


async def _serialize_invite_campaign(
    db: AsyncSession,
    campaign: InviteCampaignModel,
) -> AdminInviteCampaignResponse:
    version = (
        await db.get(InviteCampaignVersionModel, campaign.current_version_id) if campaign.current_version_id else None
    )
    payload = AdminInviteCampaignResponse.model_validate(campaign)
    return payload.model_copy(
        update={
            "current_version": (
                AdminInviteCampaignVersionResponse.model_validate(version) if version is not None else None
            )
        }
    )


async def _build_invite_tree_response(db: AsyncSession, root_invite_code_id: UUID) -> AdminInviteTreeResponse:
    root = await db.get(InviteCodeModel, root_invite_code_id)
    if root is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite tree was not found")

    invite_result = await db.execute(
        select(InviteCodeModel)
        .where(InviteCodeModel.root_invite_code_id == root_invite_code_id)
        .order_by(InviteCodeModel.generation_depth.asc(), InviteCodeModel.created_at.asc())
    )
    invites = list(invite_result.scalars().all())
    if not any(invite.id == root.id for invite in invites):
        invites.insert(0, root)

    child_counts: dict[UUID, int] = {}
    for invite in invites:
        if invite.parent_invite_code_id is not None:
            child_counts[invite.parent_invite_code_id] = child_counts.get(invite.parent_invite_code_id, 0) + 1

    edge_result = await db.execute(
        select(InviteTreeEdgeModel)
        .where(InviteTreeEdgeModel.root_invite_code_id == root_invite_code_id)
        .order_by(InviteTreeEdgeModel.generation_depth.asc(), InviteTreeEdgeModel.created_at.asc())
    )
    edges = list(edge_result.scalars().all())
    used_count = sum(1 for invite in invites if invite.is_used)
    return AdminInviteTreeResponse(
        root_invite_code_id=root_invite_code_id,
        nodes=[
            AdminInviteTreeNodeResponse(
                invite_code_id=invite.id,
                parent_invite_code_id=invite.parent_invite_code_id,
                root_invite_code_id=invite.root_invite_code_id or invite.id,
                owner_user_id=invite.owner_user_id,
                used_by_user_id=invite.used_by_user_id,
                generation_depth=invite.generation_depth,
                status=invite.status,
                grant_mode=invite.grant_mode,
                grant_plan_id=invite.grant_plan_id,
                child_batch_id=None,
                granted_plan_id=invite.grant_plan_id or invite.plan_id,
                granted_plan_code=_grant_plan_code(invite.grant_snapshot),
                child_count=child_counts.get(invite.id, 0),
                created_at=invite.created_at,
                used_at=invite.used_at,
            )
            for invite in invites
        ],
        edges=[
            AdminInviteTreeEdgeResponse(
                id=edge.id,
                root_invite_code_id=edge.root_invite_code_id,
                parent_invite_code_id=edge.parent_invite_code_id,
                redeemed_invite_code_id=edge.redeemed_invite_code_id,
                redemption_id=edge.redemption_id,
                inviter_user_id=edge.inviter_user_id,
                invitee_user_id=edge.invitee_user_id,
                generation_depth=edge.generation_depth,
                status=edge.status,
                child_batch_id=edge.child_batch_id,
                granted_plan_id=edge.granted_plan_id,
                granted_plan_code=edge.granted_plan_code,
            )
            for edge in edges
        ],
        stats={
            **await _build_invite_tree_stats(db, root_invite_code_id),
            "total_invites": len(invites),
            "used_invites": used_count,
            "available_invites": len(invites) - used_count,
        },
    )


async def _build_invite_tree_stats(db: AsyncSession, root_invite_code_id: UUID) -> dict[str, object]:
    total_nodes = await db.execute(
        select(func.count())
        .select_from(InviteCodeModel)
        .where(InviteCodeModel.root_invite_code_id == root_invite_code_id)
    )
    total_redeemed = await db.execute(
        select(func.count())
        .select_from(InviteCodeModel)
        .where(
            InviteCodeModel.root_invite_code_id == root_invite_code_id,
            InviteCodeModel.is_used.is_(True),
        )
    )
    child_issued = await db.execute(
        select(func.coalesce(func.sum(InviteBatchModel.issued_count), 0)).where(
            InviteBatchModel.root_invite_code_id == root_invite_code_id,
            InviteBatchModel.batch_kind == "child_after_redemption",
        )
    )
    max_depth = await db.execute(
        select(func.coalesce(func.max(InviteCodeModel.generation_depth), 0)).where(
            InviteCodeModel.root_invite_code_id == root_invite_code_id
        )
    )
    return {
        "total_nodes": int(total_nodes.scalar_one() or 0),
        "total_redeemed": int(total_redeemed.scalar_one() or 0),
        "total_child_invites_issued": int(child_issued.scalar_one() or 0),
        "max_depth_reached": int(max_depth.scalar_one() or 0),
    }


def _grant_plan_code(snapshot: dict | None) -> str | None:
    value = (snapshot or {}).get("plan_code")
    return value if isinstance(value, str) and value else None


async def _ensure_raw_export_allowed(db: AsyncSession, batch: InviteBatchModel) -> None:
    export_policy: dict[str, object] = {}
    if batch.invite_campaign_version_id is not None:
        version = await db.get(InviteCampaignVersionModel, batch.invite_campaign_version_id)
        if version is not None:
            export_policy = dict(version.export_policy or {})
    if not export_policy and batch.invite_campaign_id is not None:
        campaign = await db.get(InviteCampaignModel, batch.invite_campaign_id)
        if campaign is not None:
            export_policy = dict(campaign.export_policy or {})
    if export_policy and export_policy.get("raw_export_enabled") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Raw invite code export is disabled for this campaign",
        )


async def _can_return_raw_codes(db: AsyncSession, batch: InviteBatchModel, current_user: AdminUserModel) -> bool:
    try:
        await _ensure_raw_export_allowed(db, batch)
    except HTTPException:
        return False
    try:
        role = AdminRole(current_user.role)
    except ValueError:
        return False
    return has_permission(role, Permission.GROWTH_CODE_SETS_EXPORT)


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _serialize_admin_invite_batch_detail(
    db: AsyncSession,
    batch: InviteBatchModel,
) -> AdminInviteBatchDetailResponse:
    invites = await _list_invite_codes_for_batch(db, batch.id)
    payload = AdminInviteBatchResponse.model_validate(batch).model_dump()
    return AdminInviteBatchDetailResponse(
        **payload,
        invites=[_serialize_admin_invite_code(invite) for invite in invites],
    )


def _batch_audit_snapshot(batch: InviteBatchModel) -> dict[str, object]:
    return {
        "id": str(batch.id),
        "owner_user_id": str(batch.owner_user_id) if batch.owner_user_id else None,
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
        partition_key=str(batch.owner_user_id or batch.id),
        event_payload={
            "invite_batch_id": str(batch.id),
            "owner_user_id": str(batch.owner_user_id) if batch.owner_user_id else None,
            "status": batch.status,
            "requested_count": batch.requested_count,
            "issued_count": batch.issued_count,
            **payload_extra,
        },
        actor_context=OutboxActorContext(principal_type="admin", principal_id=str(current_user.id)),
        source_context={"source_use_case": "admin_invite_batch_route"},
    )
