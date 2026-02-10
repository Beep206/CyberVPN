"""Promo code API routes.

Provides:
- ``POST /promo/validate``              -- mobile user validates a promo code
- ``POST /admin/promo-codes``           -- admin creates a promo code
- ``GET  /admin/promo-codes``           -- admin lists all promo codes
- ``GET  /admin/promo-codes/{promo_id}``-- admin gets promo detail
- ``PUT  /admin/promo-codes/{promo_id}``-- admin updates a promo code
- ``DELETE /admin/promo-codes/{promo_id}``-- admin deactivates a promo code
"""

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.promo_codes.admin_manage_promo import AdminManagePromoUseCase
from src.application.use_cases.promo_codes.validate_promo import ValidatePromoUseCase
from src.domain.enums import AdminRole
from src.domain.exceptions import (
    PromoCodeExhaustedError,
    PromoCodeInvalidError,
    PromoCodeNotFoundError,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreatePromoRequest,
    PromoCodeResponse,
    UpdatePromoRequest,
    ValidatePromoRequest,
    ValidatePromoResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["promo-codes"])


# ---------------------------------------------------------------------------
# Mobile endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/promo/validate",
    response_model=ValidatePromoResponse,
    summary="Validate a promo code",
    responses={
        404: {"description": "Promo code not found"},
        422: {"description": "Promo code invalid for given parameters"},
    },
)
async def validate_promo(
    body: ValidatePromoRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> ValidatePromoResponse:
    """Validate a promo code and calculate the discount for the authenticated mobile user."""
    repo = PromoCodeRepository(db)
    use_case = ValidatePromoUseCase(repo)

    try:
        result = await use_case.execute(
            code=body.code,
            user_id=user_id,
            plan_id=body.plan_id,
            amount=Decimal(str(body.amount)) if body.amount is not None else None,
        )
    except PromoCodeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found") from None
    except PromoCodeInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    except PromoCodeExhaustedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Promo code usage limit reached",
        ) from None

    return ValidatePromoResponse(**result)


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/admin/promo-codes",
    response_model=PromoCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: create a promo code",
)
async def admin_create_promo(
    body: CreatePromoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PromoCodeResponse:
    """Create a new promo code (admin only)."""
    repo = PromoCodeRepository(db)
    use_case = AdminManagePromoUseCase(repo)

    result = await use_case.create(
        code=body.code,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        created_by=current_user.id,
        max_uses=body.max_uses,
        is_single_use=body.is_single_use,
        plan_ids=body.plan_ids,
        min_amount=body.min_amount,
        expires_at=body.expires_at,
        description=body.description,
        currency=body.currency,
    )

    return PromoCodeResponse.model_validate(result)


@router.get(
    "/admin/promo-codes",
    response_model=list[PromoCodeResponse],
    summary="Admin: list all promo codes",
)
async def admin_list_promos(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> list[PromoCodeResponse]:
    """List all promo codes with pagination (admin only)."""
    repo = PromoCodeRepository(db)
    use_case = AdminManagePromoUseCase(repo)

    promos = await use_case.list_all(offset=offset, limit=limit)
    return [PromoCodeResponse.model_validate(p) for p in promos]


@router.get(
    "/admin/promo-codes/{promo_id}",
    response_model=PromoCodeResponse,
    summary="Admin: get promo code detail",
    responses={404: {"description": "Promo code not found"}},
)
async def admin_get_promo(
    promo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PromoCodeResponse:
    """Get a single promo code by ID (admin only)."""
    repo = PromoCodeRepository(db)
    use_case = AdminManagePromoUseCase(repo)

    try:
        promo = await use_case.get_detail(promo_id)
    except PromoCodeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found") from None

    return PromoCodeResponse.model_validate(promo)


@router.put(
    "/admin/promo-codes/{promo_id}",
    response_model=PromoCodeResponse,
    summary="Admin: update a promo code",
    responses={404: {"description": "Promo code not found"}},
)
async def admin_update_promo(
    promo_id: UUID,
    body: UpdatePromoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PromoCodeResponse:
    """Update an existing promo code (admin only)."""
    repo = PromoCodeRepository(db)
    use_case = AdminManagePromoUseCase(repo)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update",
        )

    try:
        promo = await use_case.update(promo_id, **update_data)
    except PromoCodeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found") from None

    return PromoCodeResponse.model_validate(promo)


@router.delete(
    "/admin/promo-codes/{promo_id}",
    response_model=PromoCodeResponse,
    summary="Admin: deactivate a promo code",
    responses={404: {"description": "Promo code not found"}},
)
async def admin_deactivate_promo(
    promo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> PromoCodeResponse:
    """Deactivate a promo code by setting is_active=False (admin only)."""
    repo = PromoCodeRepository(db)
    use_case = AdminManagePromoUseCase(repo)

    try:
        promo = await use_case.deactivate(promo_id)
    except PromoCodeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found") from None

    return PromoCodeResponse.model_validate(promo)
