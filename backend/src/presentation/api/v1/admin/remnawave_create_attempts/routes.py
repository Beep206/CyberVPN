from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from httpx import HTTPStatusError, RequestError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempt_settlement import (
    RemnawaveCustomerCreateAttemptConflict,
    RemnawaveCustomerCreateAttemptNotFound,
    RemnawaveCustomerCreateAttemptResult,
    RemnawaveCustomerCreateAttemptSettlementService,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.remnawave.client import RemnawaveClient, RemnawaveProtocolError
from src.infrastructure.remnawave.user_gateway import RemnawaveIdentityBindingError, RemnawaveUserGateway
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.api.v1.admin.remnawave_create_attempts.schemas import (
    CustomerCreateAttemptTransitionResponse,
    ReopenCustomerCreateAttemptRequest,
    SettleCustomerCreateAttemptRequest,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_role

router = APIRouter(
    prefix="/admin/remnawave/customer-create-attempts",
    tags=["admin", "remnawave", "reconciliation"],
)


def _response(result: RemnawaveCustomerCreateAttemptResult) -> CustomerCreateAttemptTransitionResponse:
    return CustomerCreateAttemptTransitionResponse(
        attempt_id=result.attempt_id,
        customer_account_id=result.customer_account_id,
        state=result.state,
        changed=result.changed,
        provider_numeric_user_id=result.user_ref.id if result.user_ref is not None else None,
        provider_legacy_uuid=result.user_ref.legacy_uuid if result.user_ref is not None else None,
    )


async def _rollback_and_raise(db: AsyncSession, *, status_code: int, detail: str) -> NoReturn:
    await db.rollback()
    raise HTTPException(status_code=status_code, detail=detail)


@router.post(
    "/{attempt_id}/settle",
    response_model=CustomerCreateAttemptTransitionResponse,
    responses={
        404: {"description": "Customer create attempt not found"},
        409: {"description": "Attempt or provider identity cannot be settled safely"},
        503: {"description": "Authoritative provider readback unavailable"},
    },
)
async def settle_customer_create_attempt(
    attempt_id: Annotated[UUID, Path()],
    body: SettleCustomerCreateAttemptRequest,
    request: Request,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> CustomerCreateAttemptTransitionResponse:
    service = RemnawaveCustomerCreateAttemptSettlementService(db, RemnawaveUserGateway(client))
    try:
        result = await service.settle(
            attempt_id=attempt_id,
            provider_numeric_user_id=body.provider_numeric_user_id,
            provider_legacy_uuid=body.provider_legacy_uuid,
        )
    except RemnawaveCustomerCreateAttemptNotFound:
        await _rollback_and_raise(db, status_code=status.HTTP_404_NOT_FOUND, detail="Customer create attempt not found")
    except (RemnawaveCustomerCreateAttemptConflict, RemnawaveIdentityBindingError):
        await _rollback_and_raise(
            db,
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer create attempt cannot be settled with that provider identity",
        )
    except (HTTPStatusError, RequestError, RemnawaveProtocolError):
        await _rollback_and_raise(
            db,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authoritative Remnawave user readback is unavailable",
        )

    if result.changed:
        await write_required_admin_audit_entry(
            db=db,
            action="remnawave.customer_create_attempt.settled",
            resource_type="remnawave_user_create_attempt",
            resource_id=result.attempt_id,
            actor=current_admin,
            request=request,
            details={
                "outcome": result.state,
                "customer_account_id": result.customer_account_id,
                "provider_numeric_user_id": body.provider_numeric_user_id,
                "provider_legacy_uuid_present": body.provider_legacy_uuid is not None,
                "reason_code": body.reason_code,
            },
        )
    await db.commit()
    return _response(result)


@router.post(
    "/{attempt_id}/reopen",
    response_model=CustomerCreateAttemptTransitionResponse,
    responses={
        404: {"description": "Customer create attempt not found"},
        409: {"description": "Attempt cannot be reopened"},
    },
)
async def reopen_customer_create_attempt(
    attempt_id: Annotated[UUID, Path()],
    body: ReopenCustomerCreateAttemptRequest,
    request: Request,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CustomerCreateAttemptTransitionResponse:
    service = RemnawaveCustomerCreateAttemptSettlementService(db, None)
    try:
        result = await service.reopen(attempt_id=attempt_id)
    except RemnawaveCustomerCreateAttemptNotFound:
        await _rollback_and_raise(db, status_code=status.HTTP_404_NOT_FOUND, detail="Customer create attempt not found")
    except RemnawaveCustomerCreateAttemptConflict:
        await _rollback_and_raise(
            db,
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer create attempt cannot be reopened",
        )

    await write_required_admin_audit_entry(
        db=db,
        action="remnawave.customer_create_attempt.reopened",
        resource_type="remnawave_user_create_attempt",
        resource_id=result.attempt_id,
        actor=current_admin,
        request=request,
        details={
            "outcome": result.state,
            "customer_account_id": result.customer_account_id,
            "reason_code": body.reason_code,
            "provider_mutation_rearmed": False,
        },
    )
    await db.commit()
    return _response(result)
