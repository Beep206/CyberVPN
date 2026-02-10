"""Partner API routes for mobile users and admin."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.partners.admin_promote_partner import AdminPromotePartnerUseCase
from src.application.use_cases.partners.bind_partner import BindPartnerUseCase
from src.application.use_cases.partners.create_partner_code import CreatePartnerCodeUseCase
from src.application.use_cases.partners.partner_dashboard import PartnerDashboardUseCase
from src.domain.enums import AdminRole
from src.domain.exceptions import (
    DomainError,
    MarkupExceedsLimitError,
    PartnerCodeNotFoundError,
    UserAlreadyBoundToPartnerError,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    BindPartnerRequest,
    CreatePartnerCodeRequest,
    PartnerCodeResponse,
    PartnerDashboardResponse,
    PartnerEarningResponse,
    PromotePartnerRequest,
    UpdateMarkupRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["partners"])


# ---------------------------------------------------------------------------
# Partner (mobile-user) endpoints
# ---------------------------------------------------------------------------


@router.post("/partner/codes", response_model=PartnerCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_partner_code(
    body: CreatePartnerCodeRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> PartnerCodeResponse:
    """Create a new partner referral code with an optional markup percentage."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    partner_repo = PartnerRepository(db)

    use_case = CreatePartnerCodeUseCase(partner_repo, config_service)
    try:
        code_model = await use_case.execute(user_id, body.code, body.markup_pct)
    except MarkupExceedsLimitError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return code_model


@router.get("/partner/codes", response_model=list[PartnerCodeResponse])
async def list_partner_codes(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerCodeResponse]:
    """List all partner codes owned by the authenticated user."""
    partner_repo = PartnerRepository(db)
    codes = await partner_repo.get_codes_by_partner(user_id)
    return codes


@router.put("/partner/codes/{code_id}", response_model=PartnerCodeResponse)
async def update_partner_code_markup(
    code_id: UUID,
    body: UpdateMarkupRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> PartnerCodeResponse:
    """Update the markup percentage on a partner code owned by the authenticated user."""
    partner_repo = PartnerRepository(db)
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)

    code_model = await partner_repo.get_code_by_id(code_id)
    if code_model is None or code_model.partner_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner code not found")

    max_markup = await config_service.get_partner_max_markup_pct()
    if body.markup_pct > max_markup:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Markup {body.markup_pct}% exceeds maximum {max_markup}%",
        )

    code_model.markup_pct = body.markup_pct
    updated = await partner_repo.update_code(code_model)
    return updated


@router.get("/partner/dashboard", response_model=PartnerDashboardResponse)
async def get_partner_dashboard(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> PartnerDashboardResponse:
    """Return aggregated partner dashboard data."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    partner_repo = PartnerRepository(db)

    use_case = PartnerDashboardUseCase(partner_repo, config_service)
    try:
        result = await use_case.execute(user_id)
    except DomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return PartnerDashboardResponse(
        total_clients=result["total_clients"],
        total_earned=result["total_earned"],
        current_tier=result["current_tier"],
        codes=[
            {
                "id": str(c.id),
                "code": c.code,
                "markup_pct": float(c.markup_pct),
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
            }
            for c in result["codes"]
        ],
    )


@router.get("/partner/earnings", response_model=list[PartnerEarningResponse])
async def list_partner_earnings(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[PartnerEarningResponse]:
    """List recent earnings for the authenticated partner."""
    partner_repo = PartnerRepository(db)
    earnings = await partner_repo.get_earnings_by_partner(user_id)
    return earnings


@router.post("/partner/bind", status_code=status.HTTP_200_OK)
async def bind_to_partner(
    body: BindPartnerRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bind the authenticated user to a partner via a partner code."""
    partner_repo = PartnerRepository(db)
    use_case = BindPartnerUseCase(db, partner_repo)
    try:
        await use_case.execute(user_id, body.partner_code)
    except PartnerCodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except UserAlreadyBoundToPartnerError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"status": "bound"}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.post("/admin/partners/promote", status_code=status.HTTP_200_OK)
async def admin_promote_partner(
    body: PromotePartnerRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin action to promote a mobile user to partner status."""
    use_case = AdminPromotePartnerUseCase(db)
    try:
        user = await use_case.execute(body.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"status": "promoted", "user_id": str(user.id)}
