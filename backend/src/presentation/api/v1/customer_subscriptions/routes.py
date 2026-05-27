from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.customer_subscriptions import (
    CustomerSubscriptionServiceAccessUseCase,
    GetCustomerSubscriptionEntitlementsUseCase,
    ListCustomerSubscriptionsUseCase,
    SelectedSubscriptionCheckoutUseCase,
)
from src.application.use_cases.payments.checkout import CheckoutAddonInput
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.domain.exceptions import InsufficientWalletBalanceError, WalletNotFoundError
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionConfigResponse
from src.presentation.api.v1.access_delivery_channels.routes import (
    _serialize_access_delivery_channel,
    _serialize_purchase_context,
)
from src.presentation.api.v1.access_delivery_channels.schemas import (
    CurrentServiceStateConsumptionContextResponse,
    CurrentServiceStateResponse,
    GetCurrentServiceStateRequest,
)
from src.presentation.api.v1.device_credentials.routes import _serialize_device_credential
from src.presentation.api.v1.entitlements.schemas import CurrentEntitlementStateResponse
from src.presentation.api.v1.payments.schemas import CheckoutCommitResponse, CheckoutQuoteResponse, InvoiceResponse
from src.presentation.api.v1.provisioning_profiles.routes import _serialize_provisioning_profile
from src.presentation.api.v1.service_identities.routes import _serialize_service_identity
from src.presentation.api.v1.subscriptions.routes import _serialize_subscription_quote
from src.presentation.api.v1.subscriptions.schemas import (
    PurchaseSubscriptionAddonsRequest,
    UpgradeSubscriptionRequest,
)
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.services import get_crypto_client

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


@router.post("/{subscription_key}/service-state", response_model=CurrentServiceStateResponse)
async def get_customer_subscription_service_state(
    subscription_key: str,
    payload: GetCurrentServiceStateRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> CurrentServiceStateResponse:
    try:
        result = await CustomerSubscriptionServiceAccessUseCase(db).get_service_state(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            subscription_key=subscription_key,
            provider_name=payload.provider_name,
            channel_type=payload.channel_type.value if payload.channel_type else None,
            channel_subject_ref=payload.channel_subject_ref,
            provisioning_profile_key=payload.provisioning_profile_key,
            remnawave_client=remnawave_client,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CurrentServiceStateResponse(
        customer_account_id=customer_account_id,
        auth_realm_id=current_realm.auth_realm.id,
        provider_name=payload.provider_name,
        entitlement_snapshot=CurrentEntitlementStateResponse(**result.entitlement_snapshot),
        service_identity=(
            _serialize_service_identity(result.service_identity) if result.service_identity is not None else None
        ),
        provisioning_profile=(
            _serialize_provisioning_profile(result.provisioning_profile)
            if result.provisioning_profile is not None
            else None
        ),
        device_credential=(
            _serialize_device_credential(result.device_credential)
            if getattr(result, "device_credential", None) is not None
            else None
        ),
        access_delivery_channel=(
            _serialize_access_delivery_channel(result.access_delivery_channel)
            if result.access_delivery_channel is not None
            else None
        ),
        purchase_context=_serialize_purchase_context(result.active_entitlement_grant),
        consumption_context=CurrentServiceStateConsumptionContextResponse(
            channel_type=payload.channel_type,
            channel_subject_ref=(
                result.resolved_channel_subject_ref or payload.channel_subject_ref
            ),
            provisioning_profile_key=(
                result.resolved_provisioning_profile_key or payload.provisioning_profile_key
            ),
            credential_type=payload.credential_type,
            credential_subject_key=payload.credential_subject_key,
        ),
    )


@router.get("/{subscription_key}/config", response_model=RemnawaveSubscriptionConfigResponse)
async def get_customer_subscription_config(
    subscription_key: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> RemnawaveSubscriptionConfigResponse:
    try:
        return await CustomerSubscriptionServiceAccessUseCase(db).get_config(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            subscription_key=subscription_key,
            remnawave_client=remnawave_client,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{subscription_key}/upgrade/quote", response_model=CheckoutQuoteResponse)
async def quote_customer_subscription_upgrade(
    subscription_key: str,
    body: UpgradeSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
):
    try:
        result = await SelectedSubscriptionCheckoutUseCase(db).quote_upgrade(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            subscription_key=subscription_key,
            target_plan_id=body.target_plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_subscription_quote(result)


@router.post("/{subscription_key}/upgrade", response_model=CheckoutCommitResponse)
async def commit_customer_subscription_upgrade(
    subscription_key: str,
    body: UpgradeSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> CheckoutCommitResponse:
    try:
        result = await SelectedSubscriptionCheckoutUseCase(db).quote_upgrade(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            subscription_key=subscription_key,
            target_plan_id=body.target_plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
        )
        quote = _serialize_subscription_quote(result)
        commit_result = await CommitCheckoutUseCase(db, crypto_client).execute(
            user_id=customer_account_id,
            quote_result=result,
            currency=body.currency,
            channel=body.channel,
            description=f"CyberVPN selected subscription upgrade to {result.plan_name or 'plan'}",
            payload=f"{customer_account_id}:{body.target_plan_id}:selected-upgrade:{subscription_key}",
            checkout_mode="selected_subscription_upgrade",
            payment_plan_id=result.plan_id,
            metadata_extra={"target_subscription_key": subscription_key},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (InsufficientWalletBalanceError, WalletNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upgrade processing failed",
        ) from exc

    invoice = InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
    return CheckoutCommitResponse(
        **quote.model_dump(),
        payment_id=commit_result.payment.id,
        status=commit_result.status,
        invoice=invoice,
    )


@router.post("/{subscription_key}/addons/quote", response_model=CheckoutQuoteResponse)
async def quote_customer_subscription_addons(
    subscription_key: str,
    body: PurchaseSubscriptionAddonsRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
):
    try:
        result = await SelectedSubscriptionCheckoutUseCase(db).quote_addons(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            subscription_key=subscription_key,
            addons=[
                CheckoutAddonInput(
                    code=addon.code,
                    qty=addon.qty,
                    location_code=addon.location_code,
                )
                for addon in body.addons
            ],
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_subscription_quote(result)


@router.post("/{subscription_key}/addons", response_model=CheckoutCommitResponse)
async def purchase_customer_subscription_addons(
    subscription_key: str,
    body: PurchaseSubscriptionAddonsRequest,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> CheckoutCommitResponse:
    try:
        result = await SelectedSubscriptionCheckoutUseCase(db).quote_addons(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            subscription_key=subscription_key,
            addons=[
                CheckoutAddonInput(
                    code=addon.code,
                    qty=addon.qty,
                    location_code=addon.location_code,
                )
                for addon in body.addons
            ],
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
            sale_channel=body.channel,
        )
        quote = _serialize_subscription_quote(result)
        commit_result = await CommitCheckoutUseCase(db, crypto_client).execute(
            user_id=customer_account_id,
            quote_result=result,
            currency=body.currency,
            channel=body.channel,
            description=f"CyberVPN add-ons for selected subscription {subscription_key}",
            payload=f"{customer_account_id}:{result.plan_id}:selected-addons:{subscription_key}",
            checkout_mode="selected_subscription_addons",
            payment_plan_id=None,
            use_quote_plan_id_for_payment=False,
            subscription_days_override=result.duration_days,
            metadata_extra={
                "target_subscription_key": subscription_key,
                "base_plan_id": str(result.plan_id) if result.plan_id else None,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (InsufficientWalletBalanceError, WalletNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Add-on purchase processing failed",
        ) from exc

    invoice = InvoiceResponse(**asdict(commit_result.invoice)) if commit_result.invoice is not None else None
    return CheckoutCommitResponse(
        **quote.model_dump(),
        payment_id=commit_result.payment.id,
        status=commit_result.status,
        invoice=invoice,
    )


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
