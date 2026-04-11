"""Admin routes for referral and partner analytics."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel, PartnerEarningModel
from src.infrastructure.database.models.referral_commission_model import ReferralCommissionModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.referral_commission_repo import ReferralCommissionRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

from .growth_schemas import (
    AdminGrowthUserSummary,
    AdminPartnerDetailResponse,
    AdminPartnerListItemResponse,
    AdminPartnersListResponse,
    AdminReferralCommissionRecord,
    AdminReferralOverviewResponse,
    AdminReferralReferrerRow,
    AdminReferralUserDetailResponse,
)

router = APIRouter(prefix="/admin", tags=["admin", "growth"])


def _serialize_user_summary(user: MobileUserModel | None) -> AdminGrowthUserSummary | None:
    if user is None:
        return None

    return AdminGrowthUserSummary(
        id=user.id,
        email=user.email,
        username=user.username,
        telegram_username=user.telegram_username,
        referral_code=user.referral_code,
        is_partner=user.is_partner,
    )


def _serialize_referral_commission(
    commission: ReferralCommissionModel,
    users_by_id: dict[UUID, MobileUserModel],
) -> AdminReferralCommissionRecord:
    return AdminReferralCommissionRecord(
        id=commission.id,
        referrer_user_id=commission.referrer_user_id,
        referred_user_id=commission.referred_user_id,
        payment_id=commission.payment_id,
        commission_rate=float(commission.commission_rate),
        base_amount=float(commission.base_amount),
        commission_amount=float(commission.commission_amount),
        currency=commission.currency,
        created_at=commission.created_at,
        referrer=_serialize_user_summary(users_by_id.get(commission.referrer_user_id)),
        referred_user=_serialize_user_summary(users_by_id.get(commission.referred_user_id)),
    )


def _serialize_partner_list_item(
    user: MobileUserModel,
    stats: dict[str, object] | None,
) -> AdminPartnerListItemResponse:
    resolved_stats = stats or {}
    return AdminPartnerListItemResponse(
        user=_serialize_user_summary(user),
        promoted_at=user.partner_promoted_at,
        code_count=int(resolved_stats.get("code_count", 0) or 0),
        active_code_count=int(resolved_stats.get("active_code_count", 0) or 0),
        total_clients=int(resolved_stats.get("total_clients", 0) or 0),
        total_earned=float(resolved_stats.get("total_earned", 0) or 0),
        last_activity_at=resolved_stats.get("last_activity_at"),
    )


@router.get("/referrals/overview", response_model=AdminReferralOverviewResponse)
async def get_referral_overview(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminReferralOverviewResponse:
    referral_repo = ReferralCommissionRepository(db)
    mobile_user_repo = MobileUserRepository(db)

    overview = await referral_repo.get_admin_overview_metrics()
    recent_commissions = await referral_repo.get_recent(limit=10)
    top_referrers_stats = await referral_repo.get_top_referrer_stats(limit=10)

    user_ids = {
        commission.referrer_user_id
        for commission in recent_commissions
    } | {
        commission.referred_user_id
        for commission in recent_commissions
    } | {
        stat["referrer_user_id"]
        for stat in top_referrers_stats
    }

    users = await mobile_user_repo.list_by_ids(list(user_ids))
    users_by_id = {user.id: user for user in users}

    route_operations_total.labels(route="admin_referrals", action="overview", status="success").inc()
    return AdminReferralOverviewResponse(
        total_commissions=int(overview["total_commissions"]),
        total_earned=float(overview["total_earned"]),
        unique_referrers=int(overview["unique_referrers"]),
        unique_referred_users=int(overview["unique_referred_users"]),
        recent_commissions=[
            _serialize_referral_commission(commission, users_by_id)
            for commission in recent_commissions
        ],
        top_referrers=[
            AdminReferralReferrerRow(
                user=_serialize_user_summary(users_by_id.get(stat["referrer_user_id"])),
                commission_count=int(stat["commission_count"]),
                referred_users=int(stat["referred_users"]),
                total_earned=float(stat["total_earned"]),
                last_commission_at=stat["last_commission_at"],
            )
            for stat in top_referrers_stats
            if users_by_id.get(stat["referrer_user_id"]) is not None
        ],
    )


@router.get("/referrals/users/{user_id}", response_model=AdminReferralUserDetailResponse)
async def get_referral_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminReferralUserDetailResponse:
    mobile_user_repo = MobileUserRepository(db)
    referral_repo = ReferralCommissionRepository(db)

    user = await mobile_user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile user not found")

    recent_commissions = await referral_repo.get_by_referrer(user_id, limit=20)
    stats_map = await referral_repo.get_referrer_stats_map([user_id])
    stats = stats_map.get(
        user_id,
        {
            "commission_count": 0,
            "referred_users": 0,
            "total_earned": 0,
            "last_commission_at": None,
        },
    )

    related_user_ids = {user.id}
    related_user_ids.update(commission.referred_user_id for commission in recent_commissions)
    users = await mobile_user_repo.list_by_ids(list(related_user_ids))
    users_by_id = {item.id: item for item in users}

    route_operations_total.labels(route="admin_referrals", action="user_detail", status="success").inc()
    return AdminReferralUserDetailResponse(
        user=_serialize_user_summary(user),
        referred_by_user_id=user.referred_by_user_id,
        commission_count=int(stats["commission_count"]),
        referred_users=int(stats["referred_users"]),
        total_earned=float(stats["total_earned"]),
        recent_commissions=[
            _serialize_referral_commission(commission, users_by_id)
            for commission in recent_commissions
        ],
    )


@router.get("/partners", response_model=AdminPartnersListResponse)
async def list_partners(
    search: str | None = Query(None, description="Search by email, username, telegram, UUID, referral code"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.VIEW_ANALYTICS)),
) -> AdminPartnersListResponse:
    mobile_user_repo = MobileUserRepository(db)
    partner_repo = PartnerRepository(db)

    users = await mobile_user_repo.list_admin(
        search=search,
        is_partner=True,
        offset=offset,
        limit=limit,
    )
    total = await mobile_user_repo.count_admin(search=search, is_partner=True)
    stats_map = await partner_repo.get_partner_stats_map([user.id for user in users])

    route_operations_total.labels(route="admin_partners", action="list", status="success").inc()
    return AdminPartnersListResponse(
        items=[
            _serialize_partner_list_item(user, stats_map.get(user.id))
            for user in users
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/partners/{user_id}", response_model=AdminPartnerDetailResponse)
async def get_partner_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.USER_READ)),
) -> AdminPartnerDetailResponse:
    mobile_user_repo = MobileUserRepository(db)
    partner_repo = PartnerRepository(db)

    user = await mobile_user_repo.get_by_id(user_id)
    if user is None or not user.is_partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

    stats_map = await partner_repo.get_partner_stats_map([user_id])
    stats = stats_map.get(user_id, {})
    codes = await partner_repo.get_codes_by_partner(user_id)
    earnings = await partner_repo.get_earnings_by_partner(user_id, limit=20)

    route_operations_total.labels(route="admin_partners", action="detail", status="success").inc()
    return AdminPartnerDetailResponse(
        **_serialize_partner_list_item(user, stats).model_dump(),
        codes=[code for code in codes],
        recent_earnings=[earning for earning in earnings],
    )

