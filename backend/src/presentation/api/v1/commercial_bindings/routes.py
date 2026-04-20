from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.commercial_bindings import (
    CreateCustomerCommercialBindingUseCase,
    GetCustomerCommercialBindingUseCase,
    ListCustomerCommercialBindingsUseCase,
)
from src.domain.enums import AdminRole, CustomerCommercialBindingStatus, CustomerCommercialBindingType
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateCustomerCommercialBindingRequest, CustomerCommercialBindingResponse

router = APIRouter(prefix="/commercial-bindings", tags=["commercial-bindings"])


def _serialize_binding(model) -> CustomerCommercialBindingResponse:
    return CustomerCommercialBindingResponse(
        id=model.id,
        user_id=model.user_id,
        auth_realm_id=model.auth_realm_id,
        storefront_id=model.storefront_id,
        binding_type=model.binding_type,
        binding_status=model.binding_status,
        owner_type=model.owner_type,
        partner_account_id=model.partner_account_id,
        partner_code_id=model.partner_code_id,
        reason_code=model.reason_code,
        evidence_payload=dict(model.evidence_payload or {}),
        created_by_admin_user_id=model.created_by_admin_user_id,
        effective_from=model.effective_from,
        effective_to=model.effective_to,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=CustomerCommercialBindingResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_commercial_binding(
    payload: CreateCustomerCommercialBindingRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> CustomerCommercialBindingResponse:
    use_case = CreateCustomerCommercialBindingUseCase(db)
    try:
        created = await use_case.execute(
            user_id=payload.user_id,
            binding_type=payload.binding_type.value,
            owner_type=payload.owner_type.value,
            storefront_id=payload.storefront_id,
            partner_code=payload.partner_code,
            partner_code_id=payload.partner_code_id,
            partner_account_id=payload.partner_account_id,
            reason_code=payload.reason_code,
            evidence_payload=payload.evidence_payload,
            created_by_admin_user_id=current_admin.id,
            effective_from=payload.effective_from,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_binding(created)


@router.get("/", response_model=list[CustomerCommercialBindingResponse])
async def list_customer_commercial_bindings(
    user_id: UUID | None = Query(None),
    storefront_id: UUID | None = Query(None),
    binding_type: CustomerCommercialBindingType | None = Query(None),
    binding_status: CustomerCommercialBindingStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[CustomerCommercialBindingResponse]:
    use_case = ListCustomerCommercialBindingsUseCase(db)
    items = await use_case.execute(
        user_id=user_id,
        storefront_id=storefront_id,
        binding_type=binding_type.value if binding_type else None,
        binding_status=binding_status.value if binding_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_binding(item) for item in items]


@router.get("/{binding_id}", response_model=CustomerCommercialBindingResponse)
async def get_customer_commercial_binding(
    binding_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> CustomerCommercialBindingResponse:
    use_case = GetCustomerCommercialBindingUseCase(db)
    item = await use_case.execute(binding_id=binding_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer commercial binding not found")
    return _serialize_binding(item)
