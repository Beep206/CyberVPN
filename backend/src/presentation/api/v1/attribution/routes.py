from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.attribution import (
    GetAttributionTouchpointUseCase,
    GetOrderAttributionResultUseCase,
    ListAttributionTouchpointsUseCase,
    RecordAttributionTouchpointUseCase,
    ResolveOrderAttributionUseCase,
)
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AttributionTouchpointResponse,
    OrderAttributionResultResponse,
    RecordAttributionTouchpointRequest,
)

router = APIRouter(prefix="/attribution", tags=["attribution"])


def _serialize_touchpoint(model) -> AttributionTouchpointResponse:
    return AttributionTouchpointResponse(
        id=model.id,
        touchpoint_type=model.touchpoint_type,
        user_id=model.user_id,
        auth_realm_id=model.auth_realm_id,
        storefront_id=model.storefront_id,
        quote_session_id=model.quote_session_id,
        checkout_session_id=model.checkout_session_id,
        order_id=model.order_id,
        partner_code_id=model.partner_code_id,
        sale_channel=model.sale_channel,
        source_host=model.source_host,
        source_path=model.source_path,
        campaign_params=dict(model.campaign_params or {}),
        evidence_payload=dict(model.evidence_payload or {}),
        occurred_at=model.occurred_at,
        created_at=model.created_at,
    )


def _serialize_order_attribution_result(model) -> OrderAttributionResultResponse:
    return OrderAttributionResultResponse(
        id=model.id,
        order_id=model.order_id,
        user_id=model.user_id,
        auth_realm_id=model.auth_realm_id,
        storefront_id=model.storefront_id,
        owner_type=model.owner_type,
        owner_source=model.owner_source,
        partner_account_id=model.partner_account_id,
        partner_code_id=model.partner_code_id,
        winning_touchpoint_id=model.winning_touchpoint_id,
        winning_binding_id=model.winning_binding_id,
        rule_path=list(model.rule_path or []),
        evidence_snapshot=model.evidence_snapshot or {},
        explainability_snapshot=model.explainability_snapshot or {},
        policy_snapshot=model.policy_snapshot or {},
        resolved_at=model.resolved_at,
        created_at=model.created_at,
    )


async def _resolve_target_realm(
    *,
    db: AsyncSession,
    current_realm: RealmResolution,
    auth_realm_id: UUID | None,
    auth_realm_key: str | None,
) -> RealmResolution:
    if auth_realm_id is None and auth_realm_key is None:
        return current_realm

    repo = AuthRealmRepository(db)
    auth_realm = None
    if auth_realm_id is not None:
        auth_realm = await repo.get_realm_by_id(auth_realm_id)
    elif auth_realm_key is not None:
        auth_realm = await repo.get_realm_by_key(auth_realm_key)

    if auth_realm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth realm not found")

    return RealmResolution(auth_realm=auth_realm, source="admin_override")


@router.post(
    "/touchpoints",
    response_model=AttributionTouchpointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_touchpoint(
    payload: RecordAttributionTouchpointRequest,
    db: AsyncSession = Depends(get_db),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AttributionTouchpointResponse:
    target_realm = await _resolve_target_realm(
        db=db,
        current_realm=current_realm,
        auth_realm_id=payload.auth_realm_id,
        auth_realm_key=payload.auth_realm_key,
    )
    use_case = RecordAttributionTouchpointUseCase(db)
    try:
        created = await use_case.execute(
            current_realm=target_realm,
            touchpoint_type=payload.touchpoint_type.value,
            user_id=payload.user_id,
            storefront_id=payload.storefront_id,
            quote_session_id=payload.quote_session_id,
            checkout_session_id=payload.checkout_session_id,
            order_id=payload.order_id,
            partner_code=payload.partner_code,
            partner_code_id=payload.partner_code_id,
            sale_channel=payload.sale_channel,
            source_host=payload.source_host,
            source_path=payload.source_path,
            campaign_params=payload.campaign_params,
            evidence_payload=payload.evidence_payload,
            occurred_at=payload.occurred_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_touchpoint(created)


@router.get("/touchpoints", response_model=list[AttributionTouchpointResponse])
async def list_touchpoints(
    user_id: UUID | None = Query(None),
    quote_session_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[AttributionTouchpointResponse]:
    use_case = ListAttributionTouchpointsUseCase(db)
    items = await use_case.execute(
        user_id=user_id,
        quote_session_id=quote_session_id,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )
    return [_serialize_touchpoint(item) for item in items]


@router.get("/touchpoints/{touchpoint_id}", response_model=AttributionTouchpointResponse)
async def get_touchpoint(
    touchpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> AttributionTouchpointResponse:
    use_case = GetAttributionTouchpointUseCase(db)
    item = await use_case.execute(touchpoint_id=touchpoint_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribution touchpoint not found")
    return _serialize_touchpoint(item)


@router.post("/orders/{order_id}/resolve", response_model=OrderAttributionResultResponse)
async def resolve_order_attribution(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> OrderAttributionResultResponse:
    use_case = ResolveOrderAttributionUseCase(db)
    try:
        item = await use_case.execute(order_id=order_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return _serialize_order_attribution_result(item)


@router.get("/orders/{order_id}/result", response_model=OrderAttributionResultResponse)
async def get_order_attribution_result(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> OrderAttributionResultResponse:
    use_case = GetOrderAttributionResultUseCase(db)
    item = await use_case.execute(order_id=order_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order attribution result not found")
    return _serialize_order_attribution_result(item)
