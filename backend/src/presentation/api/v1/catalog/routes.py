from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.public_catalog import (
    PublicCatalogContext,
    PublicCommercialCatalog,
    ResolvePublicCatalogContextUseCase,
    ResolvePublicCommercialCatalogUseCase,
)
from src.domain.entities.commercial_context import CommercialContextSignals
from src.presentation.dependencies.database import get_db

from .schemas import (
    PaymentMethodAvailabilityResponse,
    PublicCatalogAddonResponse,
    PublicCatalogBillingPeriodResponse,
    PublicCatalogContextResponse,
    PublicCatalogMetadataResponse,
    PublicCatalogMoneyResponse,
    PublicCatalogPlanResponse,
    PublicCatalogQuoteHandoffResponse,
    PublicCommercialCatalogResponse,
    ResolveCatalogContextRequest,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/context", response_model=PublicCatalogContextResponse)
async def resolve_public_catalog_context(
    payload: ResolveCatalogContextRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PublicCatalogContextResponse:
    use_case = ResolvePublicCatalogContextUseCase(db)
    try:
        context = await use_case.execute(
            signals=_build_signals(payload, request),
            channel=payload.channel_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_context(context)


@router.get("", response_model=PublicCommercialCatalogResponse, include_in_schema=False)
@router.get("/", response_model=PublicCommercialCatalogResponse)
async def get_public_catalog(
    request: Request,
    channel: str = Query("web", min_length=1, max_length=80),
    country: str | None = Query(None, min_length=2, max_length=2),
    currency: str | None = Query(None, min_length=3, max_length=3),
    ui_locale: str | None = Query(None, alias="uiLocale", max_length=20),
    url_locale: str | None = Query(None, alias="urlLocale", max_length=20),
    storefront_key: str | None = Query(None, alias="storefrontKey", min_length=1, max_length=80),
    db: AsyncSession = Depends(get_db),
) -> PublicCommercialCatalogResponse:
    payload = ResolveCatalogContextRequest(
        urlLocale=url_locale,
        explicitUiLocale=ui_locale,
        explicitCountryCode=country,
        explicitCurrencyCode=currency,
        channelKey=channel,
    )
    use_case = ResolvePublicCommercialCatalogUseCase(db)
    try:
        catalog = await use_case.execute(
            signals=_build_signals(payload, request),
            channel=channel,
            storefront_key=storefront_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_catalog(catalog)


def _build_signals(payload: ResolveCatalogContextRequest, request: Request) -> CommercialContextSignals:
    explicit_display_country = payload.explicit_display_country_code or payload.explicit_country_code
    explicit_pricing_country = payload.explicit_pricing_country_code or payload.explicit_country_code
    cookie_country = (
        payload.cookie_country_code or request.cookies.get("cybervpn_country") or request.cookies.get("country_code")
    )
    cookie_currency = (
        payload.cookie_currency_code or request.cookies.get("cybervpn_currency") or request.cookies.get("currency_code")
    )
    return CommercialContextSignals(
        url_locale=payload.url_locale,
        browser_language=payload.browser_language or request.headers.get("Accept-Language"),
        telegram_language_code=payload.telegram_language_code,
        explicit_ui_locale=payload.explicit_ui_locale,
        explicit_display_country_code=explicit_display_country,
        explicit_pricing_country_code=explicit_pricing_country,
        explicit_currency_code=payload.explicit_currency_code,
        session_country_code=payload.session_country_code,
        session_currency_code=payload.session_currency_code,
        cookie_country_code=cookie_country,
        cookie_currency_code=cookie_currency,
        channel_key=payload.channel_key,
        channel_default_locale=payload.channel_default_locale,
        fallback_country_code=payload.fallback_country_code,
    )


def _serialize_catalog(catalog: PublicCommercialCatalog) -> PublicCommercialCatalogResponse:
    return PublicCommercialCatalogResponse(
        catalogVersion=catalog.catalog_version,
        cacheKey=catalog.cache_key,
        context=_serialize_context(catalog.context),
        plans=[
            PublicCatalogPlanResponse(
                planCode=plan.plan_code,
                displayName=plan.display_name,
                version=plan.version,
                billingPeriods=[
                    PublicCatalogBillingPeriodResponse(
                        planId=period.plan_id,
                        catalogItemKey=period.catalog_item_key,
                        durationDays=period.duration_days,
                        displayPrice=_serialize_money(period.display_price),
                        version=period.version,
                        quote=PublicCatalogQuoteHandoffResponse(
                            planId=period.quote.plan_id,
                            planCode=period.quote.plan_code,
                            billingPeriodDays=period.quote.billing_period_days,
                            currency=period.quote.currency,
                            catalogItemKey=period.quote.catalog_item_key,
                            contextCacheKey=period.quote.context_cache_key,
                        ),
                        includedAddonCodes=list(period.included_addon_codes),
                        availability=list(period.availability),
                        metadata=period.metadata,
                    )
                    for period in plan.billing_periods
                ],
                devicesIncluded=plan.devices_included,
                trafficLimitBytes=plan.traffic_limit_bytes,
                trafficPolicy=plan.traffic_policy,
                connectionModes=list(plan.connection_modes),
                serverPool=list(plan.server_pool),
                supportSla=plan.support_sla,
                dedicatedIp=plan.dedicated_ip,
                inviteBundle=plan.invite_bundle,
                trialEligible=plan.trial_eligible,
                promoEligible=plan.promo_eligible,
                metadata=plan.metadata,
            )
            for plan in catalog.plans
        ],
        addons=[
            PublicCatalogAddonResponse(
                addonId=addon.addon_id,
                code=addon.code,
                displayName=addon.display_name,
                durationMode=addon.duration_mode,
                isStackable=addon.is_stackable,
                quantityStep=addon.quantity_step,
                displayPrice=_serialize_money(addon.display_price),
                maxQuantityByPlan=addon.max_quantity_by_plan,
                deltaEntitlements=addon.delta_entitlements,
                requiresLocation=addon.requires_location,
                saleChannels=list(addon.sale_channels),
                metadata=addon.metadata,
            )
            for addon in catalog.addons
        ],
        trialEligible=catalog.trial_eligible,
        promoEligible=catalog.promo_eligible,
        metadata=PublicCatalogMetadataResponse(
            policyIds=list(catalog.metadata.policy_ids),
            source=catalog.metadata.source,
            channel=catalog.metadata.channel,
            storefrontKey=catalog.metadata.storefront_key,
            addonsEnabled=catalog.metadata.addons_enabled,
            promoCodesEnabled=catalog.metadata.promo_codes_enabled,
            checkoutCodeDiscountsEnabled=catalog.metadata.checkout_code_discounts_enabled,
            invalidationEvents=list(catalog.metadata.invalidation_events),
        ),
    )


def _serialize_context(context: PublicCatalogContext) -> PublicCatalogContextResponse:
    resolved = context.resolved
    payment_methods = context.payment_methods
    return PublicCatalogContextResponse(
        uiLocale=resolved.ui_locale,
        displayCountry=resolved.display_country,
        pricingCountry=resolved.pricing_country,
        paymentCountry=resolved.payment_country,
        currency=resolved.currency,
        confidence=resolved.confidence,
        selectableCountries=list(resolved.selectable_countries),
        selectableCurrencies=list(resolved.selectable_currencies),
        paymentMethods=PaymentMethodAvailabilityResponse(
            availableMethods=list(payment_methods.available_methods),
            webCheckout=payment_methods.web_checkout,
            cryptobot=payment_methods.cryptobot,
            telegramStars=payment_methods.telegram_stars,
            manualInvoice=payment_methods.manual_invoice,
            autorenewal=payment_methods.autorenewal,
        ),
        cacheKey=context.cache_key,
        resolutionTrace=list(resolved.resolution_trace),
    )


def _serialize_money(money) -> PublicCatalogMoneyResponse:
    return PublicCatalogMoneyResponse(
        amount=money.amount,
        currency=money.currency,
        minorUnits=money.minor_units,
    )
