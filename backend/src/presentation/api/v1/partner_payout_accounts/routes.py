from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.settlement import (
    ArchivePartnerPayoutAccountUseCase,
    CreatePartnerPayoutAccountUseCase,
    EvaluatePartnerPayoutAccountEligibilityUseCase,
    GetPartnerPayoutAccountUseCase,
    ListPartnerPayoutAccountsUseCase,
    MakeDefaultPartnerPayoutAccountUseCase,
    SuspendPartnerPayoutAccountUseCase,
    VerifyPartnerPayoutAccountUseCase,
)
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import (
    AdminRole,
    PartnerPayoutAccountApprovalStatus,
    PartnerPayoutAccountStatus,
    PartnerPayoutAccountVerificationStatus,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import resolve_partner_workspace_access
from src.presentation.dependencies.roles import require_role

from .schemas import (
    ArchivePartnerPayoutAccountRequest,
    CreatePartnerPayoutAccountRequest,
    PartnerPayoutAccountEligibilityResponse,
    PartnerPayoutAccountResponse,
    SuspendPartnerPayoutAccountRequest,
)

router = APIRouter(prefix="/partner-payout-accounts", tags=["partner-payout-accounts"])


def _serialize_payout_account(model) -> PartnerPayoutAccountResponse:
    return PartnerPayoutAccountResponse(
        id=model.id,
        partner_account_id=model.partner_account_id,
        settlement_profile_id=model.settlement_profile_id,
        payout_rail=model.payout_rail,
        display_label=model.display_label,
        masked_destination=model.masked_destination,
        destination_metadata=dict(model.destination_metadata or {}),
        verification_status=model.verification_status,
        approval_status=model.approval_status,
        account_status=model.account_status,
        is_default=bool(model.is_default),
        created_by_admin_user_id=model.created_by_admin_user_id,
        verified_by_admin_user_id=model.verified_by_admin_user_id,
        verified_at=model.verified_at,
        approved_by_admin_user_id=model.approved_by_admin_user_id,
        approved_at=model.approved_at,
        suspended_by_admin_user_id=model.suspended_by_admin_user_id,
        suspended_at=model.suspended_at,
        suspension_reason_code=model.suspension_reason_code,
        archived_by_admin_user_id=model.archived_by_admin_user_id,
        archived_at=model.archived_at,
        archive_reason_code=model.archive_reason_code,
        default_selected_by_admin_user_id=model.default_selected_by_admin_user_id,
        default_selected_at=model.default_selected_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
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
    if permission.value not in access.permission_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing partner workspace permission: {permission.value}",
        )


@router.post("/", response_model=PartnerPayoutAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_partner_payout_account(
    payload: CreatePartnerPayoutAccountRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerPayoutAccountResponse:
    await _require_workspace_permission(
        workspace_id=payload.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.PAYOUTS_WRITE,
    )
    try:
        item = await CreatePartnerPayoutAccountUseCase(db).execute(
            partner_account_id=payload.partner_account_id,
            payout_rail=payload.payout_rail,
            display_label=payload.display_label,
            destination_reference=payload.destination_reference,
            destination_metadata=payload.destination_metadata,
            settlement_profile_id=payload.settlement_profile_id,
            make_default=payload.make_default,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_payout_account(item)


@router.get("/", response_model=list[PartnerPayoutAccountResponse])
async def list_partner_payout_accounts(
    partner_account_id: UUID = Query(...),
    payout_account_status: PartnerPayoutAccountStatus | None = Query(None),
    verification_status: PartnerPayoutAccountVerificationStatus | None = Query(None),
    approval_status: PartnerPayoutAccountApprovalStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerPayoutAccountResponse]:
    await _require_workspace_permission(
        workspace_id=partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.PAYOUTS_READ,
    )
    items = await ListPartnerPayoutAccountsUseCase(db).execute(
        partner_account_id=partner_account_id,
        payout_account_status=payout_account_status.value if payout_account_status else None,
        verification_status=verification_status.value if verification_status else None,
        approval_status=approval_status.value if approval_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_payout_account(item) for item in items]


@router.get("/{payout_account_id}", response_model=PartnerPayoutAccountResponse)
async def get_partner_payout_account(
    payout_account_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerPayoutAccountResponse:
    item = await GetPartnerPayoutAccountUseCase(db).execute(payout_account_id=payout_account_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner payout account not found")
    await _require_workspace_permission(
        workspace_id=item.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.PAYOUTS_READ,
    )
    return _serialize_payout_account(item)


@router.get("/{payout_account_id}/eligibility", response_model=PartnerPayoutAccountEligibilityResponse)
async def get_partner_payout_account_eligibility(
    payout_account_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerPayoutAccountEligibilityResponse:
    item = await GetPartnerPayoutAccountUseCase(db).execute(payout_account_id=payout_account_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner payout account not found")
    await _require_workspace_permission(
        workspace_id=item.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.PAYOUTS_READ,
    )
    try:
        result = await EvaluatePartnerPayoutAccountEligibilityUseCase(db).execute(
            payout_account_id=payout_account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PartnerPayoutAccountEligibilityResponse(
        partner_payout_account_id=result.partner_payout_account_id,
        partner_account_id=result.partner_account_id,
        eligible=result.eligible,
        reason_codes=result.reason_codes,
        blocking_risk_review_ids=result.blocking_risk_review_ids,
        active_reserve_ids=result.active_reserve_ids,
        checked_at=result.checked_at,
    )


@router.post("/{payout_account_id}/make-default", response_model=PartnerPayoutAccountResponse)
async def make_partner_payout_account_default(
    payout_account_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerPayoutAccountResponse:
    item = await GetPartnerPayoutAccountUseCase(db).execute(payout_account_id=payout_account_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner payout account not found")
    await _require_workspace_permission(
        workspace_id=item.partner_account_id,
        current_user=current_user,
        db=db,
        permission=PartnerPermission.PAYOUTS_WRITE,
    )
    try:
        updated = await MakeDefaultPartnerPayoutAccountUseCase(db).execute(
            payout_account_id=payout_account_id,
            selected_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_payout_account(updated)


@router.post("/{payout_account_id}/verify", response_model=PartnerPayoutAccountResponse)
async def verify_partner_payout_account(
    payout_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PartnerPayoutAccountResponse:
    try:
        item = await VerifyPartnerPayoutAccountUseCase(db).execute(
            payout_account_id=payout_account_id,
            verified_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_payout_account(item)


@router.post("/{payout_account_id}/suspend", response_model=PartnerPayoutAccountResponse)
async def suspend_partner_payout_account(
    payout_account_id: UUID,
    payload: SuspendPartnerPayoutAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PartnerPayoutAccountResponse:
    try:
        item = await SuspendPartnerPayoutAccountUseCase(db).execute(
            payout_account_id=payout_account_id,
            suspended_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_payout_account(item)


@router.post("/{payout_account_id}/archive", response_model=PartnerPayoutAccountResponse)
async def archive_partner_payout_account(
    payout_account_id: UUID,
    payload: ArchivePartnerPayoutAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PartnerPayoutAccountResponse:
    try:
        item = await ArchivePartnerPayoutAccountUseCase(db).execute(
            payout_account_id=payout_account_id,
            archived_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_payout_account(item)
