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
        payload.cookie_country_code
        or request.cookies.get("cybervpn_country")
        or request.cookies.get("country_code")
    )
    cookie_currency = (
        payload.cookie_currency_code
        or request.cookies.get("cybervpn_currency")
        or request.cookies.get("currency_code")
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
        catalog_version=catalog.catalog_version,
        cache_key=catalog.cache_key,
        context=_serialize_context(catalog.context),
        plans=[
            PublicCatalogPlanResponse(
                plan_code=plan.plan_code,
                display_name=plan.display_name,
                version=plan.version,
                billing_periods=[
                    PublicCatalogBillingPeriodResponse(
                        plan_id=period.plan_id,
                        catalog_item_key=period.catalog_item_key,
                        duration_days=period.duration_days,
                        display_price=_serialize_money(period.display_price),
                        version=period.version,
                        quote=PublicCatalogQuoteHandoffResponse(
                            plan_id=period.quote.plan_id,
                            plan_code=period.quote.plan_code,
                            billing_period_days=period.quote.billing_period_days,
                            currency=period.quote.currency,
                            catalog_item_key=period.quote.catalog_item_key,
                            context_cache_key=period.quote.context_cache_key,
                        ),
                        included_addon_codes=list(period.included_addon_codes),
                        availability=list(period.availability),
                        metadata=period.metadata,
                    )
                    for period in plan.billing_periods
                ],
                devices_included=plan.devices_included,
                traffic_limit_bytes=plan.traffic_limit_bytes,
                traffic_policy=plan.traffic_policy,
                connection_modes=list(plan.connection_modes),
                server_pool=list(plan.server_pool),
                support_sla=plan.support_sla,
                dedicated_ip=plan.dedicated_ip,
                invite_bundle=plan.invite_bundle,
                trial_eligible=plan.trial_eligible,
                promo_eligible=plan.promo_eligible,
                metadata=plan.metadata,
            )
            for plan in catalog.plans
        ],
        addons=[
            PublicCatalogAddonResponse(
                addon_id=addon.addon_id,
                code=addon.code,
                display_name=addon.display_name,
                duration_mode=addon.duration_mode,
                is_stackable=addon.is_stackable,
                quantity_step=addon.quantity_step,
                display_price=_serialize_money(addon.display_price),
                max_quantity_by_plan=addon.max_quantity_by_plan,
                delta_entitlements=addon.delta_entitlements,
                requires_location=addon.requires_location,
                sale_channels=list(addon.sale_channels),
                metadata=addon.metadata,
            )
            for addon in catalog.addons
        ],
        trial_eligible=catalog.trial_eligible,
        promo_eligible=catalog.promo_eligible,
        metadata=PublicCatalogMetadataResponse(
            policy_ids=list(catalog.metadata.policy_ids),
            source=catalog.metadata.source,
            channel=catalog.metadata.channel,
            storefront_key=catalog.metadata.storefront_key,
            addons_enabled=catalog.metadata.addons_enabled,
            promo_codes_enabled=catalog.metadata.promo_codes_enabled,
            checkout_code_discounts_enabled=catalog.metadata.checkout_code_discounts_enabled,
            invalidation_events=list(catalog.metadata.invalidation_events),
        ),
    )


def _serialize_context(context: PublicCatalogContext) -> PublicCatalogContextResponse:
    resolved = context.resolved
    payment_methods = context.payment_methods
    return PublicCatalogContextResponse(
        ui_locale=resolved.ui_locale,
        display_country=resolved.display_country,
        pricing_country=resolved.pricing_country,
        payment_country=resolved.payment_country,
        currency=resolved.currency,
        confidence=resolved.confidence,
        selectable_countries=list(resolved.selectable_countries),
        selectable_currencies=list(resolved.selectable_currencies),
        payment_methods=PaymentMethodAvailabilityResponse(
            available_methods=list(payment_methods.available_methods),
            web_checkout=payment_methods.web_checkout,
            cryptobot=payment_methods.cryptobot,
            telegram_stars=payment_methods.telegram_stars,
            manual_invoice=payment_methods.manual_invoice,
            autorenewal=payment_methods.autorenewal,
        ),
        cache_key=context.cache_key,
        resolution_trace=list(resolved.resolution_trace),
    )


def _serialize_money(money) -> PublicCatalogMoneyResponse:
    return PublicCatalogMoneyResponse(
        amount=money.amount,
        currency=money.currency,
        minor_units=money.minor_units,
    )
