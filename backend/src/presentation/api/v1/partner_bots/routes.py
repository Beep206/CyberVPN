from __future__ import annotations

import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.partner_bots import (
    ClaimPartnerBotProvisioningJobUseCase,
    CreatePartnerBotUseCase,
    FinalizePartnerBotProvisioningJobUseCase,
    GetPartnerBotUseCase,
    ListPartnerBotsUseCase,
    PartnerBotBundle,
    RequestPartnerBotProvisioningUseCase,
    RestorePartnerBotUseCase,
    RotatePartnerBotTokenUseCase,
    SuspendPartnerBotUseCase,
)
from src.config.settings import settings
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import PartnerBotStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    enforce_partner_workspace_permission,
    resolve_partner_workspace_access,
)

from .schemas import (
    ClaimPartnerBotProvisioningJobRequest,
    ClaimPartnerBotProvisioningJobResponse,
    CreatePartnerBotRequest,
    FinalizePartnerBotProvisioningJobRequest,
    PartnerBotProvisioningJobResponse,
    PartnerBotResponse,
    RequestPartnerBotProvisioningRequest,
    RotatePartnerBotTokenRequest,
    SuspendPartnerBotRequest,
)

router = APIRouter(prefix="/partner-bots", tags=["partner-bots"])


def _is_valid_telegram_bot_secret(secret: str | None) -> bool:
    configured = settings.telegram_bot_internal_secret.get_secret_value().strip()
    if not configured or not secret:
        return False
    return hmac.compare_digest(secret.strip(), configured)


def _require_telegram_bot_secret(secret: str | None) -> None:
    if _is_valid_telegram_bot_secret(secret):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _serialize_provisioning_job(latest_job) -> PartnerBotProvisioningJobResponse | None:
    if latest_job is None:
        return None
    return PartnerBotProvisioningJobResponse(
        id=latest_job.id,
        partner_bot_id=latest_job.partner_bot_id,
        partner_account_id=latest_job.partner_account_id,
        requested_by_admin_user_id=latest_job.requested_by_admin_user_id,
        provisioning_path=latest_job.provisioning_path,
        job_status=latest_job.job_status,
        attempt_count=latest_job.attempt_count,
        request_payload=dict(latest_job.request_payload or {}),
        result_payload=dict(latest_job.result_payload or {}),
        last_error=latest_job.last_error,
        queued_at=latest_job.queued_at,
        started_at=latest_job.started_at,
        completed_at=latest_job.completed_at,
        created_at=latest_job.created_at,
        updated_at=latest_job.updated_at,
    )


def _serialize_partner_bot_bundle(bundle: PartnerBotBundle) -> PartnerBotResponse:
    latest_job = bundle.latest_provisioning_job
    return PartnerBotResponse(
        id=bundle.bot.id,
        partner_account_id=bundle.bot.partner_account_id,
        storefront_id=bundle.bot.storefront_id,
        bot_key=bundle.bot.bot_key,
        display_name=bundle.bot.display_name,
        short_description=bundle.bot.short_description,
        long_description=bundle.bot.long_description,
        telegram_bot_id=bundle.bot.telegram_bot_id,
        telegram_username=bundle.bot.telegram_username,
        managed_by_bot_id=bundle.bot.managed_by_bot_id,
        default_locale=bundle.bot.default_locale,
        primary_color=bundle.bot.primary_color,
        provisioning_path=bundle.bot.provisioning_path,
        token_status=bundle.bot.token_status,
        status=bundle.bot.status,
        release_channel=bundle.bot.release_channel,
        provisioning_last_error=bundle.bot.provisioning_last_error,
        provisioning_requested_at=bundle.bot.provisioning_requested_at,
        provisioned_at=bundle.bot.provisioned_at,
        suspended_at=bundle.bot.suspended_at,
        suspension_reason_code=bundle.bot.suspension_reason_code,
        created_by_admin_user_id=bundle.bot.created_by_admin_user_id,
        updated_by_admin_user_id=bundle.bot.updated_by_admin_user_id,
        created_at=bundle.bot.created_at,
        updated_at=bundle.bot.updated_at,
        latest_provisioning_job=_serialize_provisioning_job(latest_job),
    )


async def _require_workspace_permission(
    *,
    workspace_id: UUID,
    current_user: AdminUserModel,
    db: AsyncSession,
    permission: PartnerPermission,
) -> None:
    access = await resolve_partner_workspace_access(
        workspace_id=workspace_id,
        current_user=current_user,
        db=db,
    )
    await enforce_partner_workspace_permission(
        access=access,
        permission=permission,
        current_user=current_user,
        db=db,
    )


@router.get("/", response_model=list[PartnerBotResponse])
async def list_partner_bots(
    partner_account_id: UUID = Query(...),
    bot_status: PartnerBotStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerBotResponse]:
    await _require_workspace_permission(
        workspace_id=partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_READ,
    )
    items = await ListPartnerBotsUseCase(db).execute(
        partner_account_id=partner_account_id,
        bot_status=bot_status.value if bot_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_partner_bot_bundle(item) for item in items]


@router.post("/", response_model=PartnerBotResponse, status_code=status.HTTP_201_CREATED)
async def create_partner_bot(
    payload: CreatePartnerBotRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    await _require_workspace_permission(
        workspace_id=payload.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_WRITE,
    )
    try:
        item = await CreatePartnerBotUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            bot_key=payload.bot_key,
            display_name=payload.display_name,
            default_locale=payload.default_locale,
            primary_color=payload.primary_color,
            short_description=payload.short_description,
            long_description=payload.long_description,
            storefront_id=payload.storefront_id,
            release_channel=payload.release_channel,
            provisioning_path=payload.provisioning_path.value,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_partner_bot_bundle(item)


@router.get("/{partner_bot_id}", response_model=PartnerBotResponse)
async def get_partner_bot(
    partner_bot_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    item = await GetPartnerBotUseCase(db).execute(partner_bot_id=partner_bot_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner bot not found")
    await _require_workspace_permission(
        workspace_id=item.bot.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_READ,
    )
    return _serialize_partner_bot_bundle(item)


@router.post("/{partner_bot_id}/provision", response_model=PartnerBotResponse)
async def request_partner_bot_provisioning(
    partner_bot_id: UUID,
    payload: RequestPartnerBotProvisioningRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    existing = await GetPartnerBotUseCase(db).execute(partner_bot_id=partner_bot_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner bot not found")
    await _require_workspace_permission(
        workspace_id=existing.bot.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_WRITE,
    )
    try:
        item = await RequestPartnerBotProvisioningUseCase(db).execute(
            partner_bot_id=partner_bot_id,
            requested_by_admin_user_id=current_user.id,
            provisioning_path=payload.provisioning_path.value if payload.provisioning_path else None,
            request_payload=payload.request_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_partner_bot_bundle(item)


@router.post("/{partner_bot_id}/suspend", response_model=PartnerBotResponse)
async def suspend_partner_bot(
    partner_bot_id: UUID,
    payload: SuspendPartnerBotRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    existing = await GetPartnerBotUseCase(db).execute(partner_bot_id=partner_bot_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner bot not found")
    await _require_workspace_permission(
        workspace_id=existing.bot.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_WRITE,
    )
    try:
        item = await SuspendPartnerBotUseCase(db).execute(
            partner_bot_id=partner_bot_id,
            suspended_by_admin_user_id=current_user.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_partner_bot_bundle(item)


@router.post("/{partner_bot_id}/restore", response_model=PartnerBotResponse)
async def restore_partner_bot(
    partner_bot_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    existing = await GetPartnerBotUseCase(db).execute(partner_bot_id=partner_bot_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner bot not found")
    await _require_workspace_permission(
        workspace_id=existing.bot.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_WRITE,
    )
    try:
        item = await RestorePartnerBotUseCase(db).execute(
            partner_bot_id=partner_bot_id,
            restored_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_partner_bot_bundle(item)


@router.post("/{partner_bot_id}/rotate-token", response_model=PartnerBotResponse)
async def rotate_partner_bot_token(
    partner_bot_id: UUID,
    payload: RotatePartnerBotTokenRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    existing = await GetPartnerBotUseCase(db).execute(partner_bot_id=partner_bot_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner bot not found")
    await _require_workspace_permission(
        workspace_id=existing.bot.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.INTEGRATIONS_WRITE,
    )
    try:
        item = await RotatePartnerBotTokenUseCase(db).execute(
            partner_bot_id=partner_bot_id,
            requested_by_admin_user_id=current_user.id,
            request_payload=payload.request_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_partner_bot_bundle(item)


@router.post(
    "/internal/provisioning-jobs/claim",
    response_model=ClaimPartnerBotProvisioningJobResponse,
)
async def claim_partner_bot_provisioning_job(
    payload: ClaimPartnerBotProvisioningJobRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> ClaimPartnerBotProvisioningJobResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    item = await ClaimPartnerBotProvisioningJobUseCase(db).execute(
        processor_id=payload.processor_id,
        max_scan_count=payload.max_scan_count,
    )
    return ClaimPartnerBotProvisioningJobResponse(
        bot=_serialize_partner_bot_bundle(item) if item is not None else None
    )


@router.post(
    "/internal/provisioning-jobs/{partner_bot_provisioning_job_id}/finalize",
    response_model=PartnerBotResponse,
)
async def finalize_partner_bot_provisioning_job(
    partner_bot_provisioning_job_id: UUID,
    payload: FinalizePartnerBotProvisioningJobRequest,
    telegram_bot_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Secret"),
    db: AsyncSession = Depends(get_db),
) -> PartnerBotResponse:
    _require_telegram_bot_secret(telegram_bot_secret)
    try:
        item = await FinalizePartnerBotProvisioningJobUseCase(db).execute(
            partner_bot_provisioning_job_id=partner_bot_provisioning_job_id,
            processor_id=payload.processor_id,
            job_status=payload.job_status.value,
            result_payload=payload.result_payload,
            last_error=payload.last_error,
            telegram_bot_id=payload.telegram_bot_id,
            telegram_username=payload.telegram_username,
            managed_by_bot_id=payload.managed_by_bot_id,
            token_status=payload.token_status.value if payload.token_status else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_partner_bot_bundle(item)
