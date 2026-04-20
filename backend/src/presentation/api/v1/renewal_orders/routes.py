from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.renewal_orders import GetRenewalOrderUseCase, ResolveRenewalOrderUseCase
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import RenewalOrderResponse, ResolveRenewalOrderRequest

router = APIRouter(prefix="/renewal-orders", tags=["renewal-orders"])


def _serialize_renewal_order(model) -> RenewalOrderResponse:
    return RenewalOrderResponse(
        id=model.id,
        order_id=model.order_id,
        initial_order_id=model.initial_order_id,
        prior_order_id=model.prior_order_id,
        user_id=model.user_id,
        auth_realm_id=model.auth_realm_id,
        storefront_id=model.storefront_id,
        originating_attribution_result_id=model.originating_attribution_result_id,
        winning_binding_id=model.winning_binding_id,
        renewal_sequence_number=model.renewal_sequence_number,
        renewal_mode=model.renewal_mode,
        provenance_owner_type=model.provenance_owner_type,
        provenance_owner_source=model.provenance_owner_source,
        provenance_partner_account_id=model.provenance_partner_account_id,
        provenance_partner_code_id=model.provenance_partner_code_id,
        effective_owner_type=model.effective_owner_type,
        effective_owner_source=model.effective_owner_source,
        effective_partner_account_id=model.effective_partner_account_id,
        effective_partner_code_id=model.effective_partner_code_id,
        payout_eligible=bool(model.payout_eligible),
        payout_block_reason_codes=list(model.payout_block_reason_codes or []),
        lineage_snapshot=model.lineage_snapshot or {},
        explainability_snapshot=model.explainability_snapshot or {},
        policy_snapshot=model.policy_snapshot or {},
        resolved_at=model.resolved_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/resolve", response_model=RenewalOrderResponse, status_code=status.HTTP_201_CREATED)
async def resolve_renewal_order(
    payload: ResolveRenewalOrderRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.ADMIN)),
) -> RenewalOrderResponse:
    use_case = ResolveRenewalOrderUseCase(db)
    try:
        model = await use_case.execute(
            order_id=payload.order_id,
            prior_order_id=payload.prior_order_id,
            renewal_mode=payload.renewal_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_renewal_order(model)


@router.get("/{renewal_order_id}", response_model=RenewalOrderResponse)
async def get_renewal_order(
    renewal_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.SUPPORT)),
) -> RenewalOrderResponse:
    use_case = GetRenewalOrderUseCase(db)
    model = await use_case.execute(renewal_order_id=renewal_order_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Renewal order not found")
    return _serialize_renewal_order(model)


@router.get("/by-order/{order_id}", response_model=RenewalOrderResponse)
async def get_renewal_order_by_order_id(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.SUPPORT)),
) -> RenewalOrderResponse:
    use_case = GetRenewalOrderUseCase(db)
    model = await use_case.execute(order_id=order_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Renewal order not found")
    return _serialize_renewal_order(model)
