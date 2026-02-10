"""Wallet API routes for mobile users and admin."""

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.services.wallet_service import WalletService
from src.application.use_cases.wallet.admin_topup import AdminTopupUseCase
from src.application.use_cases.wallet.process_withdrawal import ProcessWithdrawalUseCase
from src.application.use_cases.wallet.request_withdrawal import RequestWithdrawalUseCase
from src.domain.enums import AdminRole
from src.domain.exceptions import (
    DomainError,
    InsufficientWalletBalanceError,
    WalletNotFoundError,
    WithdrawalBelowMinimumError,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.database.repositories.withdrawal_repo import WithdrawalRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AdminProcessWithdrawalRequest,
    AdminTopupRequest,
    WalletResponse,
    WalletTransactionResponse,
    WithdrawalResponse,
    WithdrawRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["wallet"])


# ---------------------------------------------------------------------------
# Mobile-user wallet endpoints
# ---------------------------------------------------------------------------


@router.get("/wallet", response_model=WalletResponse)
async def get_wallet(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Return the authenticated user's wallet balance."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)

    try:
        wallet = await wallet_service.get_balance(user_id)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc

    return wallet


@router.get("/wallet/transactions", response_model=list[WalletTransactionResponse])
async def list_wallet_transactions(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[WalletTransactionResponse]:
    """Return paginated wallet transaction history for the authenticated user."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)

    transactions = await wallet_service.get_transactions(user_id, offset=offset, limit=limit)
    return transactions


@router.post("/wallet/withdraw", response_model=WithdrawalResponse, status_code=status.HTTP_201_CREATED)
async def request_withdrawal(
    body: WithdrawRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalResponse:
    """Request a withdrawal from the authenticated user's wallet."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)
    withdrawal_repo = WithdrawalRepository(db)
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)

    use_case = RequestWithdrawalUseCase(wallet_service, withdrawal_repo, config_service)
    try:
        result = await use_case.execute(user_id, Decimal(str(body.amount)), body.method)
    except WithdrawalBelowMinimumError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    except InsufficientWalletBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return result


@router.get("/wallet/withdrawals", response_model=list[WithdrawalResponse])
async def list_withdrawals(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[WithdrawalResponse]:
    """Return the authenticated user's withdrawal requests."""
    withdrawal_repo = WithdrawalRepository(db)
    withdrawals = await withdrawal_repo.get_by_user(user_id)
    return withdrawals


# ---------------------------------------------------------------------------
# Admin wallet endpoints
# ---------------------------------------------------------------------------


@router.post("/admin/wallets/{user_id}/topup", response_model=WalletTransactionResponse)
async def admin_topup_wallet(
    user_id: UUID,
    body: AdminTopupRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WalletTransactionResponse:
    """Admin action to credit funds into a user's wallet."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)

    use_case = AdminTopupUseCase(wallet_service)
    try:
        tx = await use_case.execute(user_id, Decimal(str(body.amount)), body.description)
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return tx


@router.get("/admin/wallets/{user_id}", response_model=WalletResponse)
async def admin_get_wallet(
    user_id: UUID,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Admin view of a user's wallet balance."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)

    try:
        wallet = await wallet_service.get_balance(user_id)
    except WalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc

    return wallet


@router.get("/admin/withdrawals", response_model=list[WithdrawalResponse])
async def admin_list_pending_withdrawals(
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[WithdrawalResponse]:
    """Admin view of all pending withdrawal requests."""
    withdrawal_repo = WithdrawalRepository(db)
    withdrawals = await withdrawal_repo.get_pending()
    return withdrawals


@router.put("/admin/withdrawals/{withdrawal_id}/approve", response_model=WithdrawalResponse)
async def admin_approve_withdrawal(
    withdrawal_id: UUID,
    body: AdminProcessWithdrawalRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalResponse:
    """Admin action to approve a pending withdrawal request."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)
    withdrawal_repo = WithdrawalRepository(db)

    use_case = ProcessWithdrawalUseCase(withdrawal_repo, wallet_service)
    try:
        result = await use_case.approve(withdrawal_id, current_user.id, body.admin_note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return result


@router.put("/admin/withdrawals/{withdrawal_id}/reject", response_model=WithdrawalResponse)
async def admin_reject_withdrawal(
    withdrawal_id: UUID,
    body: AdminProcessWithdrawalRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalResponse:
    """Admin action to reject a pending withdrawal request."""
    wallet_repo = WalletRepository(db)
    wallet_service = WalletService(wallet_repo)
    withdrawal_repo = WithdrawalRepository(db)

    use_case = ProcessWithdrawalUseCase(withdrawal_repo, wallet_service)
    try:
        result = await use_case.reject(withdrawal_id, current_user.id, body.admin_note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return result
