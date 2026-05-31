from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResolveCatalogContextRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url_locale: str | None = Field(None, alias="urlLocale", max_length=20)
    browser_language: str | None = Field(None, alias="browserLanguage", max_length=255)
    telegram_language_code: str | None = Field(None, alias="telegramLanguageCode", max_length=20)
    explicit_ui_locale: str | None = Field(None, alias="explicitUiLocale", max_length=20)
    explicit_country_code: str | None = Field(None, alias="explicitCountryCode", min_length=2, max_length=2)
    explicit_display_country_code: str | None = Field(
        None,
        alias="explicitDisplayCountryCode",
        min_length=2,
        max_length=2,
    )
    explicit_pricing_country_code: str | None = Field(
        None,
        alias="explicitPricingCountryCode",
        min_length=2,
        max_length=2,
    )
    explicit_currency_code: str | None = Field(None, alias="explicitCurrencyCode", min_length=3, max_length=3)
    session_country_code: str | None = Field(None, alias="sessionCountryCode", min_length=2, max_length=2)
    session_currency_code: str | None = Field(None, alias="sessionCurrencyCode", min_length=3, max_length=3)
    cookie_country_code: str | None = Field(None, alias="cookieCountryCode", min_length=2, max_length=2)
    cookie_currency_code: str | None = Field(None, alias="cookieCurrencyCode", min_length=3, max_length=3)
    channel_key: str | None = Field(None, alias="channelKey", min_length=1, max_length=80)
    channel_default_locale: str | None = Field(None, alias="channelDefaultLocale", max_length=20)
    fallback_country_code: str = Field("US", alias="fallbackCountryCode", min_length=2, max_length=2)


class PaymentMethodAvailabilityResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    available_methods: list[str] = Field(alias="availableMethods")
    web_checkout: bool = Field(alias="webCheckout")
    cryptobot: bool
    telegram_stars: bool = Field(alias="telegramStars")
    manual_invoice: bool = Field(alias="manualInvoice")
    autorenewal: bool


class PublicCatalogContextResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ui_locale: str = Field(alias="uiLocale")
    display_country: str = Field(alias="displayCountry")
    pricing_country: str = Field(alias="pricingCountry")
    payment_country: str = Field(alias="paymentCountry")
    currency: str
    confidence: str
    selectable_countries: list[str] = Field(alias="selectableCountries")
    selectable_currencies: list[str] = Field(alias="selectableCurrencies")
    payment_methods: PaymentMethodAvailabilityResponse = Field(alias="paymentMethods")
    cache_key: str = Field(alias="cacheKey")
    resolution_trace: list[str] = Field(alias="resolutionTrace")


class PublicCatalogMoneyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: str
    currency: str
    minor_units: int = Field(alias="minorUnits")


class PublicCatalogQuoteHandoffResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: UUID = Field(alias="planId")
    plan_code: str = Field(alias="planCode")
    billing_period_days: int = Field(alias="billingPeriodDays")
    currency: str
    catalog_item_key: str = Field(alias="catalogItemKey")
    context_cache_key: str = Field(alias="contextCacheKey")


class PublicCatalogBillingPeriodResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: UUID = Field(alias="planId")
    catalog_item_key: str = Field(alias="catalogItemKey")
    duration_days: int = Field(alias="durationDays")
    display_price: PublicCatalogMoneyResponse = Field(alias="displayPrice")
    version: str
    quote: PublicCatalogQuoteHandoffResponse
    included_addon_codes: list[str] = Field(alias="includedAddonCodes")
    availability: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicCatalogPlanResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_code: str = Field(alias="planCode")
    display_name: str = Field(alias="displayName")
    version: str
    billing_periods: list[PublicCatalogBillingPeriodResponse] = Field(alias="billingPeriods")
    devices_included: int = Field(alias="devicesIncluded")
    traffic_limit_bytes: int | None = Field(alias="trafficLimitBytes")
    traffic_policy: dict[str, Any] = Field(alias="trafficPolicy")
    connection_modes: list[str] = Field(alias="connectionModes")
    server_pool: list[str] = Field(alias="serverPool")
    support_sla: str = Field(alias="supportSla")
    dedicated_ip: dict[str, Any] = Field(alias="dedicatedIp")
    invite_bundle: dict[str, Any] = Field(alias="inviteBundle")
    trial_eligible: bool = Field(alias="trialEligible")
    promo_eligible: bool = Field(alias="promoEligible")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicCatalogAddonResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    addon_id: UUID = Field(alias="addonId")
    code: str
    display_name: str = Field(alias="displayName")
    duration_mode: str = Field(alias="durationMode")
    is_stackable: bool = Field(alias="isStackable")
    quantity_step: int = Field(alias="quantityStep")
    display_price: PublicCatalogMoneyResponse = Field(alias="displayPrice")
    max_quantity_by_plan: dict[str, int] = Field(alias="maxQuantityByPlan")
    delta_entitlements: dict[str, Any] = Field(alias="deltaEntitlements")
    requires_location: bool = Field(alias="requiresLocation")
    sale_channels: list[str] = Field(alias="saleChannels")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicCatalogMetadataResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    policy_ids: list[str] = Field(alias="policyIds")
    source: str
    channel: str
    storefront_key: str | None = Field(alias="storefrontKey")
    addons_enabled: bool = Field(alias="addonsEnabled")
    promo_codes_enabled: bool = Field(alias="promoCodesEnabled")
    checkout_code_discounts_enabled: bool = Field(alias="checkoutCodeDiscountsEnabled")
    invalidation_events: list[str] = Field(alias="invalidationEvents")


class PublicCommercialCatalogResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    catalog_version: str = Field(alias="catalogVersion")
    cache_key: str = Field(alias="cacheKey")
    context: PublicCatalogContextResponse
    plans: list[PublicCatalogPlanResponse]
    addons: list[PublicCatalogAddonResponse]
    trial_eligible: bool = Field(alias="trialEligible")
    promo_eligible: bool = Field(alias="promoEligible")
    metadata: PublicCatalogMetadataResponse
