from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.customer_subscriptions import (
    GetCustomerSubscriptionEntitlementsUseCase,
    ListCustomerSubscriptionsUseCase,
)
from src.presentation.api.v1.entitlements.schemas import CurrentEntitlementStateResponse
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db

from .schemas import CustomerSubscriptionListResponse, CustomerSubscriptionSummaryResponse

router = APIRouter(prefix="/customer-subscriptions", tags=["customer-subscriptions"])


def _serialize_summary(item) -> CustomerSubscriptionSummaryResponse:
    return CustomerSubscriptionSummaryResponse(
        subscription_key=item.subscription_key,
        kind=item.kind,
        status=item.status,
        display_name=item.display_name,
        plan_uuid=item.plan_uuid,
        plan_code=item.plan_code,
        source_type=item.source_type,
        source_order_id=item.source_order_id,
        entitlement_grant_id=item.entitlement_grant_id,
        service_identity_id=item.service_identity_id,
        provider_name=item.provider_name,
        expires_at=item.expires_at,
        created_at=item.created_at,
        effective_entitlements=item.effective_entitlements,
        invite_bundle=item.invite_bundle,
        is_trial=item.is_trial,
        addons=item.addons,
        can_manage=item.can_manage,
        can_deliver_config=item.can_deliver_config,
        management_scope=item.management_scope,
    )


@router.get("/", response_model=CustomerSubscriptionListResponse)
async def list_customer_subscriptions(
    selected_subscription_key: str | None = Query(None, min_length=1, max_length=220),
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> CustomerSubscriptionListResponse:
    result = await ListCustomerSubscriptionsUseCase(db).execute(
        customer_account_id=customer_account_id,
        auth_realm_id=current_realm.auth_realm.id,
        selected_subscription_key=selected_subscription_key,
    )
    return CustomerSubscriptionListResponse(
        customer_account_id=result.customer_account_id,
        auth_realm_id=result.auth_realm_id,
        selected_subscription_key=result.selected_subscription_key,
        default_subscription_key=result.default_subscription_key,
        items=[_serialize_summary(item) for item in result.items],
        limitations=result.limitations,
    )


@router.get("/{subscription_key}/entitlements", response_model=CurrentEntitlementStateResponse)
async def get_customer_subscription_entitlements(
    subscription_key: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> CurrentEntitlementStateResponse:
    snapshot = await GetCustomerSubscriptionEntitlementsUseCase(db).execute(
        customer_account_id=customer_account_id,
        auth_realm_id=current_realm.auth_realm.id,
        subscription_key=subscription_key,
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return CurrentEntitlementStateResponse(**snapshot)


@router.get("/{subscription_key}", response_model=CustomerSubscriptionSummaryResponse)
async def get_customer_subscription(
    subscription_key: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> CustomerSubscriptionSummaryResponse:
    item = await ListCustomerSubscriptionsUseCase(db).get_by_key(
        customer_account_id=customer_account_id,
        auth_realm_id=current_realm.auth_realm.id,
        subscription_key=subscription_key,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return _serialize_summary(item)
