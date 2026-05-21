"""Invite code API routes.

Provides:
- ``POST /invites/redeem``        -- mobile user redeems an invite code
- ``GET  /invites/my``            -- mobile user lists their invite codes
- ``POST /admin/invite-codes``    -- admin creates invite codes
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import AdminCreateInviteRequest, InviteCodeResponse, RedeemInviteRequest

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
    response_model=list[InviteCodeResponse],
    summary="List my invite codes",
)
async def list_my_invites(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> list[InviteCodeResponse]:
    """List invite codes owned by the authenticated mobile user."""
    repo = InviteCodeRepository(db)
    invites = await repo.get_by_owner(owner_user_id=user_id, offset=offset, limit=limit)
    track_invite_operation(operation="list", success=True)
    return [InviteCodeResponse.model_validate(inv) for inv in invites]


admin_router = APIRouter(prefix="/admin/invite-codes", tags=["invites"])


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
