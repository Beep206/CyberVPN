from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.stage1_plan_policy import (
    S1_ADDON_POLICY_ID,
    S1_PAID_PLAN_POLICY_ID,
    filter_stage1_public_addons,
    filter_stage1_public_paid_plans,
)
from src.config.settings import settings
from src.domain.entities.commercial_context import (
    COUNTRY_CURRENCY_DEFAULTS,
    CommercialContextSignals,
    CountryCurrencyOption,
    CurrencyOption,
    ResolvedCommercialContext,
    normalize_currency_code,
    resolve_commercial_context,
)
from src.domain.enums import CatalogVisibility
from src.domain.services.pricing_engine import (
    ArrayOverride,
    CatalogItem,
    CatalogOverride,
    EffectiveCatalogResolver,
    PricingContext,
    build_catalog_cache_key,
)
from src.infrastructure.database.repositories.offer_repo import OfferRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.pricebook_repo import PricebookRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.metrics import (
    commerce_catalog_context_fallbacks_total,
    commerce_catalog_context_resolutions_total,
    commerce_catalog_resolution_duration_seconds,
)

PUBLIC_CATALOG_DEFAULT_CHANNEL = "web"
PUBLIC_CATALOG_ACTIVE_CHANNELS = ("web", "miniapp", "telegram_bot")
PUBLIC_CATALOG_BASE_VERSION = "public-commercial-v1"
ZERO_DECIMAL_CURRENCIES = {
    "BIF",
    "CLP",
    "DJF",
    "GNF",
    "ISK",
    "JPY",
    "KMF",
    "KRW",
    "PYG",
    "RWF",
    "UGX",
    "VND",
    "XAF",
    "XOF",
    "XPF",
    "XTR",
}


@dataclass(frozen=True)
class PublicPaymentMethodAvailability:
    available_methods: tuple[str, ...]
    web_checkout: bool
    cryptobot: bool
    telegram_stars: bool
    manual_invoice: bool
    autorenewal: bool


@dataclass(frozen=True)
class PublicCatalogContext:
    resolved: ResolvedCommercialContext
    cache_key: str
    payment_methods: PublicPaymentMethodAvailability


@dataclass(frozen=True)
class PublicCatalogMoney:
    amount: str
    currency: str
    minor_units: int


@dataclass(frozen=True)
class PublicCatalogQuoteHandoff:
    plan_id: UUID
    plan_code: str
    billing_period_days: int
    currency: str
    catalog_item_key: str
    context_cache_key: str


@dataclass(frozen=True)
class PublicCatalogBillingPeriod:
    plan_id: UUID
    catalog_item_key: str
    duration_days: int
    display_price: PublicCatalogMoney
    version: str
    quote: PublicCatalogQuoteHandoff
    included_addon_codes: tuple[str, ...] = ()
    availability: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublicCatalogPlan:
    plan_code: str
    display_name: str
    version: str
    billing_periods: tuple[PublicCatalogBillingPeriod, ...]
    devices_included: int
    traffic_limit_bytes: int | None
    traffic_policy: dict[str, Any]
    connection_modes: tuple[str, ...]
    server_pool: tuple[str, ...]
    support_sla: str
    dedicated_ip: dict[str, Any]
    invite_bundle: dict[str, Any]
    trial_eligible: bool
    promo_eligible: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublicCatalogAddon:
    addon_id: UUID
    code: str
    display_name: str
    duration_mode: str
    is_stackable: bool
    quantity_step: int
    display_price: PublicCatalogMoney
    max_quantity_by_plan: dict[str, int]
    delta_entitlements: dict[str, Any]
    requires_location: bool
    sale_channels: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublicCatalogMetadata:
    policy_ids: tuple[str, ...]
    source: str
    channel: str
    storefront_key: str | None
    addons_enabled: bool
    promo_codes_enabled: bool
    checkout_code_discounts_enabled: bool
    invalidation_events: tuple[str, ...]


@dataclass(frozen=True)
class PublicCommercialCatalog:
    catalog_version: str
    cache_key: str
    context: PublicCatalogContext
    plans: tuple[PublicCatalogPlan, ...]
    addons: tuple[PublicCatalogAddon, ...]
    trial_eligible: bool
    promo_eligible: bool
    metadata: PublicCatalogMetadata


class ResolvePublicCatalogContextUseCase:
    def __init__(
        self,
        session: AsyncSession | None,
        *,
        plan_repo: Any | None = None,
    ) -> None:
        self._plan_repo = plan_repo or SubscriptionPlanRepository(session)  # type: ignore[arg-type]

    async def execute(
        self,
        *,
        signals: CommercialContextSignals,
        channel: str | None = None,
        active_currency_codes: set[str] | None = None,
        catalog_version: str = PUBLIC_CATALOG_BASE_VERSION,
    ) -> PublicCatalogContext:
        started_at = perf_counter()
        channel_key = _normalize_channel(channel or signals.channel_key)
        try:
            active_currencies = active_currency_codes or await self._active_plan_currencies(channel=channel_key)
            resolved = resolve_commercial_context(
                replace(signals, channel_key=channel_key),
                country_options=_build_country_options(active_currencies),
                currency_options=_build_currency_options(active_currencies),
            )
            pricing_context = _pricing_context_from_resolved(resolved, channel=channel_key)
            context = PublicCatalogContext(
                resolved=resolved,
                cache_key=build_catalog_cache_key(
                    context=pricing_context,
                    catalog_version=catalog_version,
                    namespace="commercial:context",
                ),
                payment_methods=_payment_method_availability(channel_key),
            )
        except Exception:
            commerce_catalog_context_resolutions_total.labels(
                channel=channel_key,
                result="failure",
                country_source="error",
                currency_source="error",
            ).inc()
            commerce_catalog_resolution_duration_seconds.labels(
                channel=channel_key,
                result="context_failure",
            ).observe(perf_counter() - started_at)
            raise

        _record_public_catalog_context_metrics(context, channel=channel_key)
        commerce_catalog_resolution_duration_seconds.labels(
            channel=channel_key,
            result="context_success",
        ).observe(perf_counter() - started_at)
        return context

    async def _active_plan_currencies(self, *, channel: str) -> set[str]:
        plans = await self._plan_repo.list_catalog(
            visibility=CatalogVisibility.PUBLIC,
            sale_channel=channel,
            active_only=True,
        )
        public_plans = filter_stage1_public_paid_plans(plans, sale_channel=channel)
        return _collect_complete_plan_currencies(public_plans)


class ResolvePublicCommercialCatalogUseCase:
    def __init__(
        self,
        session: AsyncSession | None,
        *,
        plan_repo: Any | None = None,
        addon_repo: Any | None = None,
        offer_repo: Any | None = None,
        pricebook_repo: Any | None = None,
        resolver: EffectiveCatalogResolver | None = None,
    ) -> None:
        self._plan_repo = plan_repo or SubscriptionPlanRepository(session)  # type: ignore[arg-type]
        self._addon_repo = addon_repo or PlanAddonRepository(session)  # type: ignore[arg-type]
        self._offer_repo = offer_repo or OfferRepository(session)  # type: ignore[arg-type]
        self._pricebook_repo = pricebook_repo or PricebookRepository(session)  # type: ignore[arg-type]
        self._resolver = resolver or EffectiveCatalogResolver()

    async def execute(
        self,
        *,
        signals: CommercialContextSignals,
        channel: str | None = None,
        storefront_key: str | None = None,
    ) -> PublicCommercialCatalog:
        started_at = perf_counter()
        channel_key = _normalize_channel(channel or signals.channel_key)
        try:
            raw_plans = await self._plan_repo.list_catalog(
                visibility=CatalogVisibility.PUBLIC,
                sale_channel=channel_key,
                active_only=True,
            )
            public_plans = filter_stage1_public_paid_plans(raw_plans, sale_channel=channel_key)
            active_currencies = _collect_complete_plan_currencies(public_plans)
            context = await ResolvePublicCatalogContextUseCase(
                None,
                plan_repo=self._plan_repo,
            ).execute(
                signals=signals,
                channel=channel_key,
                active_currency_codes=active_currencies,
                catalog_version=_catalog_version(channel=channel_key, storefront_key=storefront_key),
            )
            pricing_context = _pricing_context_from_resolved(context.resolved, channel=channel_key)
            offers = await self._offer_repo.list_active(sale_channel=channel_key)
            offers_by_plan_id = _latest_offer_by_plan_id(offers)
            catalog_items, item_metadata = _build_catalog_items(public_plans, offers_by_plan_id=offers_by_plan_id)
            pricebook_overrides, pricebook_version_refs = await self._build_pricebook_overrides(
                storefront_key=storefront_key,
                currency=context.resolved.currency,
                pricing_country=context.resolved.pricing_country,
                item_key_by_plan_id={metadata["plan_id"]: key for key, metadata in item_metadata.items()},
            )
            catalog_version = _catalog_version(
                channel=channel_key,
                storefront_key=storefront_key,
                pricebook_version_refs=pricebook_version_refs,
            )
            effective_catalog = self._resolver.resolve(
                context=pricing_context,
                items=catalog_items,
                overrides=pricebook_overrides,
                catalog_version=catalog_version,
            )
            addons = await self._public_addons(channel=channel_key, currency=context.resolved.currency)

            plans = _build_public_plans(
                effective_catalog.items,
                item_metadata=item_metadata,
                context_cache_key=effective_catalog.cache_key,
            )
            catalog = PublicCommercialCatalog(
                catalog_version=catalog_version,
                cache_key=effective_catalog.cache_key,
                context=PublicCatalogContext(
                    resolved=context.resolved,
                    cache_key=effective_catalog.cache_key,
                    payment_methods=context.payment_methods,
                ),
                plans=plans,
                addons=addons,
                trial_eligible=settings.stage1_trial_provisioning_enabled
                and any(plan.trial_eligible for plan in plans),
                promo_eligible=settings.promo_codes_enabled or settings.checkout_code_discounts_enabled,
                metadata=PublicCatalogMetadata(
                    policy_ids=(S1_PAID_PLAN_POLICY_ID, S1_ADDON_POLICY_ID),
                    source="subscription_plans",
                    channel=channel_key,
                    storefront_key=storefront_key,
                    addons_enabled=settings.stage1_addons_enabled,
                    promo_codes_enabled=settings.promo_codes_enabled,
                    checkout_code_discounts_enabled=settings.checkout_code_discounts_enabled,
                    invalidation_events=effective_catalog.invalidation_events,
                ),
            )
        except Exception:
            commerce_catalog_resolution_duration_seconds.labels(
                channel=channel_key,
                result="catalog_failure",
            ).observe(perf_counter() - started_at)
            raise

        commerce_catalog_resolution_duration_seconds.labels(
            channel=channel_key,
            result="catalog_success",
        ).observe(perf_counter() - started_at)
        return catalog

    async def _build_pricebook_overrides(
        self,
        *,
        storefront_key: str | None,
        currency: str,
        pricing_country: str,
        item_key_by_plan_id: dict[UUID, str],
    ) -> tuple[tuple[CatalogOverride, ...], tuple[str, ...]]:
        if not storefront_key:
            return (), ()

        pricebooks = await self._pricebook_repo.list_active(
            storefront_key=storefront_key,
            currency_code=currency,
            region_code=pricing_country,
        )
        if not pricebooks:
            pricebooks = await self._pricebook_repo.list_active(
                storefront_key=storefront_key,
                currency_code=currency,
                region_code=None,
            )

        overrides: list[CatalogOverride] = []
        version_refs: list[str] = []
        for pricebook in pricebooks:
            version_refs.append(f"{pricebook.pricebook_key}:{pricebook.id}")
            for entry in sorted(pricebook.entries or [], key=lambda item: item.display_order):
                offer = entry.offer
                item_key = item_key_by_plan_id.get(offer.subscription_plan_id)
                if item_key is None:
                    continue
                included = tuple(
                    dict.fromkeys(
                        [
                            *(offer.included_addon_codes or []),
                            *(entry.included_addon_codes or []),
                        ]
                    )
                )
                overrides.append(
                    CatalogOverride(
                        key=f"pricebook:{pricebook.pricebook_key}:{entry.id}",
                        scope="global",
                        item_key=item_key,
                        prices={pricebook.currency_code: _decimal(entry.visible_price)},
                        addons=ArrayOverride("append", included) if included else None,
                        metadata={
                            "pricebook_key": pricebook.pricebook_key,
                            "pricebook_id": str(pricebook.id),
                            "offer_key": offer.offer_key,
                            "compare_at_price": _money_or_none(entry.compare_at_price, pricebook.currency_code),
                        },
                    )
                )
        return tuple(overrides), tuple(version_refs)

    async def _public_addons(self, *, channel: str, currency: str) -> tuple[PublicCatalogAddon, ...]:
        raw_addons = await self._addon_repo.list_catalog(active_only=True, sale_channel=channel)
        public_addons = filter_stage1_public_addons(
            raw_addons,
            sale_channel=channel,
            enabled=settings.stage1_addons_enabled,
        )
        addons: list[PublicCatalogAddon] = []
        for addon in public_addons:
            price = _addon_price(addon, currency)
            if price is None:
                continue
            addons.append(
                PublicCatalogAddon(
                    addon_id=addon.id,
                    code=addon.code,
                    display_name=addon.display_name,
                    duration_mode=addon.duration_mode,
                    is_stackable=addon.is_stackable,
                    quantity_step=addon.quantity_step,
                    display_price=price,
                    max_quantity_by_plan=dict(addon.max_quantity_by_plan or {}),
                    delta_entitlements=dict(addon.delta_entitlements or {}),
                    requires_location=addon.requires_location,
                    sale_channels=tuple(addon.sale_channels or ()),
                    metadata={"requires_quote": True},
                )
            )
        return tuple(sorted(addons, key=lambda item: item.code))


def _build_catalog_items(
    plans: list[Any],
    *,
    offers_by_plan_id: dict[UUID, Any],
) -> tuple[tuple[CatalogItem, ...], dict[str, dict[str, Any]]]:
    items: list[CatalogItem] = []
    metadata_by_key: dict[str, dict[str, Any]] = {}
    for plan in plans:
        key = str(plan.name or f"{plan.plan_code}_{plan.duration_days}")
        prices: dict[str, Decimal] = {"USD": _decimal(plan.price_usd)}
        if getattr(plan, "price_rub", None) is not None and _decimal(plan.price_rub) > 0:
            prices["RUB"] = _decimal(plan.price_rub)

        offer = offers_by_plan_id.get(plan.id)
        included_addons = tuple(offer.included_addon_codes or ()) if offer is not None else ()
        trial_eligible = bool(offer.trial_eligible) if offer is not None else bool(plan.trial_eligible)
        item_metadata = {
            "plan_id": plan.id,
            "display_name": plan.display_name or plan.name,
            "traffic_limit_bytes": plan.traffic_limit_bytes,
            "devices_included": plan.device_limit,
            "traffic_policy": dict(plan.traffic_policy or {"mode": "fair_use", "display_label": "Unlimited"}),
            "connection_modes": tuple(plan.connection_modes or ()),
            "server_pool": tuple(plan.server_pool or ()),
            "support_sla": plan.support_sla,
            "dedicated_ip": dict(plan.dedicated_ip or {"included": 0, "eligible": False}),
            "invite_bundle": dict((offer.invite_bundle if offer is not None else plan.invite_bundle) or {}),
            "trial_eligible": trial_eligible,
            "promo_eligible": settings.promo_codes_enabled or settings.checkout_code_discounts_enabled,
            "sort_order": int(plan.sort_order or 0),
            "version": (offer.offer_key if offer is not None else plan.name),
            "features": dict(plan.features or {}),
        }
        metadata_by_key[key] = item_metadata
        items.append(
            CatalogItem(
                key=key,
                plan_code=plan.plan_code,
                billing_period_days=plan.duration_days,
                prices=prices,
                addons=included_addons,
                billing_periods=(plan.duration_days,),
                availability=tuple(plan.sale_channels or ()),
                hidden=plan.catalog_visibility != CatalogVisibility.PUBLIC,
                disabled=not plan.is_active,
                metadata={"plan_id": str(plan.id), "version": item_metadata["version"]},
            )
        )
    return tuple(items), metadata_by_key


def _build_public_plans(
    effective_items: tuple[Any, ...],
    *,
    item_metadata: dict[str, dict[str, Any]],
    context_cache_key: str,
) -> tuple[PublicCatalogPlan, ...]:
    groups: dict[str, dict[str, Any]] = {}
    for item in effective_items:
        metadata = {**item_metadata[item.key], **item.metadata}
        period = PublicCatalogBillingPeriod(
            plan_id=metadata["plan_id"],
            catalog_item_key=item.key,
            duration_days=item.billing_period_days or 0,
            display_price=_money(item.price, item.currency_code),
            version=str(metadata["version"]),
            quote=PublicCatalogQuoteHandoff(
                plan_id=metadata["plan_id"],
                plan_code=item.plan_code,
                billing_period_days=item.billing_period_days or 0,
                currency=item.currency_code,
                catalog_item_key=item.key,
                context_cache_key=context_cache_key,
            ),
            included_addon_codes=tuple(item.addons),
            availability=tuple(item.availability),
            metadata={
                "applied_override_keys": tuple(item.applied_override_keys),
                "requires_quote": True,
            },
        )
        group = groups.setdefault(
            item.plan_code,
            {
                "plan_code": item.plan_code,
                "display_name": metadata["display_name"],
                "version": str(metadata["version"]),
                "periods": [],
                "devices_included": metadata["devices_included"],
                "traffic_limit_bytes": metadata["traffic_limit_bytes"],
                "traffic_policy": metadata["traffic_policy"],
                "connection_modes": metadata["connection_modes"],
                "server_pool": metadata["server_pool"],
                "support_sla": metadata["support_sla"],
                "dedicated_ip": metadata["dedicated_ip"],
                "invite_bundle": metadata["invite_bundle"],
                "trial_eligible": metadata["trial_eligible"],
                "promo_eligible": metadata["promo_eligible"],
                "sort_order": metadata["sort_order"],
                "features": metadata["features"],
            },
        )
        group["periods"].append(period)

    plans: list[PublicCatalogPlan] = []
    for group in groups.values():
        periods = tuple(sorted(group["periods"], key=lambda period: period.duration_days))
        plans.append(
            PublicCatalogPlan(
                plan_code=group["plan_code"],
                display_name=group["display_name"],
                version=group["version"],
                billing_periods=periods,
                devices_included=group["devices_included"],
                traffic_limit_bytes=group["traffic_limit_bytes"],
                traffic_policy=group["traffic_policy"],
                connection_modes=tuple(group["connection_modes"]),
                server_pool=tuple(group["server_pool"]),
                support_sla=group["support_sla"],
                dedicated_ip=group["dedicated_ip"],
                invite_bundle=group["invite_bundle"],
                trial_eligible=group["trial_eligible"],
                promo_eligible=group["promo_eligible"],
                metadata={"features": group["features"]},
            )
        )
    return tuple(sorted(plans, key=lambda plan: (groups[plan.plan_code]["sort_order"], plan.plan_code)))


def _latest_offer_by_plan_id(offers: list[Any]) -> dict[UUID, Any]:
    latest: dict[UUID, Any] = {}
    for offer in offers:
        latest.setdefault(offer.subscription_plan_id, offer)
    return latest


def _collect_complete_plan_currencies(plans: list[Any]) -> set[str]:
    if not plans:
        return {"USD"}

    currency_sets: list[set[str]] = []
    for plan in plans:
        currencies: set[str] = set()
        if _positive_money(getattr(plan, "price_usd", None)):
            currencies.add("USD")
        if _positive_money(getattr(plan, "price_rub", None)):
            currencies.add("RUB")
        if currencies:
            currency_sets.append(currencies)
    if not currency_sets:
        return {"USD"}
    complete = set.intersection(*currency_sets)
    return complete or {"USD"}


def _build_country_options(active_currency_codes: set[str]) -> list[CountryCurrencyOption]:
    active = tuple(sorted(normalize_currency_code(code) for code in (active_currency_codes or {"USD"})))
    fallback_currency = "USD" if "USD" in active else active[0]
    options: list[CountryCurrencyOption] = []
    for country_code, local_default in COUNTRY_CURRENCY_DEFAULTS.items():
        default_currency = local_default if local_default in active else fallback_currency
        supported = tuple(dict.fromkeys((default_currency, fallback_currency, *active)))
        options.append(
            CountryCurrencyOption(
                country_code=country_code,
                default_currency_code=default_currency,
                supported_currency_codes=supported,
                payment_country_code=country_code,
            )
        )
    return options


def _build_currency_options(active_currency_codes: set[str]) -> list[CurrencyOption]:
    return [
        CurrencyOption(currency_code=currency, minor_units=_minor_units(currency))
        for currency in sorted(active_currency_codes or {"USD"})
    ]


def _pricing_context_from_resolved(context: ResolvedCommercialContext, *, channel: str) -> PricingContext:
    return PricingContext(
        currency_code=context.currency,
        country_code=context.pricing_country,
        channel=channel,
    )


def _payment_method_availability(channel: str) -> PublicPaymentMethodAvailability:
    cryptobot = settings.payments_enabled
    telegram_stars = settings.telegram_stars_enabled and channel in {"miniapp", "telegram_bot"}
    manual_invoice = not settings.payments_enabled
    available_methods = tuple(
        method
        for method, enabled in (
            ("cryptobot", cryptobot),
            ("telegram_stars", telegram_stars),
            ("manual_invoice", manual_invoice),
        )
        if enabled
    )
    return PublicPaymentMethodAvailability(
        available_methods=available_methods,
        web_checkout=settings.payments_enabled,
        cryptobot=cryptobot,
        telegram_stars=telegram_stars,
        manual_invoice=manual_invoice,
        autorenewal=settings.payment_autorenewal_enabled,
    )


def _record_public_catalog_context_metrics(context: PublicCatalogContext, *, channel: str) -> None:
    trace = context.resolved.resolution_trace
    country_source = _trace_source(trace, 2)
    currency_source = _trace_source(trace, 3)
    commerce_catalog_context_resolutions_total.labels(
        channel=channel,
        result="success",
        country_source=country_source,
        currency_source=currency_source,
    ).inc()

    for fallback_type in _fallback_types(trace):
        commerce_catalog_context_fallbacks_total.labels(
            channel=channel,
            fallback_type=fallback_type,
        ).inc()


def _trace_source(trace: tuple[str, ...], index: int) -> str:
    try:
        source = trace[index]
    except IndexError:
        return "unknown"
    return source if source else "unknown"


def _fallback_types(trace: tuple[str, ...]) -> tuple[str, ...]:
    fallbacks: list[str] = []
    for source in trace:
        if source.startswith("fallback_"):
            fallbacks.append(source)
        elif source == "country_default_currency":
            fallbacks.append(source)
    return tuple(dict.fromkeys(fallbacks))


def _catalog_version(
    *,
    channel: str,
    storefront_key: str | None,
    pricebook_version_refs: tuple[str, ...] = (),
) -> str:
    parts = [PUBLIC_CATALOG_BASE_VERSION, S1_PAID_PLAN_POLICY_ID, channel]
    if storefront_key:
        parts.append(f"storefront:{storefront_key}")
    parts.extend(pricebook_version_refs)
    return ":".join(parts)


def _normalize_channel(channel: str | None) -> str:
    normalized = (channel or PUBLIC_CATALOG_DEFAULT_CHANNEL).strip().lower()
    if normalized not in PUBLIC_CATALOG_ACTIVE_CHANNELS:
        raise ValueError("Unsupported public catalog channel")
    return normalized


def _money(amount: Decimal, currency: str) -> PublicCatalogMoney:
    currency_code = normalize_currency_code(currency)
    return PublicCatalogMoney(
        amount=_format_money(amount, currency_code),
        currency=currency_code,
        minor_units=_minor_units(currency_code),
    )


def _money_or_none(amount: Any, currency: str) -> dict[str, Any] | None:
    if amount is None:
        return None
    money = _money(_decimal(amount), currency)
    return {"amount": money.amount, "currency": money.currency, "minor_units": money.minor_units}


def _addon_price(addon: Any, currency: str) -> PublicCatalogMoney | None:
    currency_code = normalize_currency_code(currency)
    if currency_code == "USD" and _positive_money(getattr(addon, "price_usd", None)):
        return _money(_decimal(addon.price_usd), currency_code)
    if currency_code == "RUB" and _positive_money(getattr(addon, "price_rub", None)):
        return _money(_decimal(addon.price_rub), currency_code)
    return None


def _format_money(amount: Decimal, currency: str) -> str:
    units = _minor_units(currency)
    quantizer = Decimal("1") if units == 0 else Decimal("1").scaleb(-units)
    return format(amount.quantize(quantizer), "f")


def _minor_units(currency: str) -> int:
    return 0 if normalize_currency_code(currency) in ZERO_DECIMAL_CURRENCIES else 2


def _positive_money(value: Any) -> bool:
    if value is None:
        return False
    try:
        return _decimal(value) > 0
    except ValueError:
        return False


def _decimal(value: Any) -> Decimal:
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid money value: {value}") from exc
