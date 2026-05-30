from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Literal

PricingScope = Literal["global", "country_group", "country", "channel", "partner", "segment", "promo"]
ArrayOverrideMode = Literal["replace", "append", "remove"]

FALLBACK_ORDER: tuple[PricingScope, ...] = (
    "global",
    "country_group",
    "country",
    "channel",
    "partner",
    "segment",
    "promo",
)

CATALOG_INVALIDATION_EVENTS: tuple[str, ...] = (
    "PriceBookPublished",
    "PriceBookRolledBack",
    "CountrySettingsChanged",
    "CountryGroupSettingsChanged",
    "ChannelSettingsChanged",
    "PartnerOverrideChanged",
    "SegmentOverrideChanged",
    "PromoPolicyChanged",
)


class PricingEngineError(ValueError):
    """Raised when an effective catalog cannot be resolved safely."""


@dataclass(frozen=True)
class PricingContext:
    currency_code: str
    country_code: str | None = None
    country_group: str | None = None
    channel: str | None = None
    partner_key: str | None = None
    segment: str | None = None
    promo_code: str | None = None

    def cache_parts(self) -> tuple[str, ...]:
        return (
            _norm_currency(self.currency_code),
            _norm_optional(self.country_group, upper=True),
            _norm_optional(self.country_code, upper=True),
            _norm_optional(self.channel),
            _norm_optional(self.partner_key),
            _norm_optional(self.segment),
            _norm_optional(self.promo_code, upper=True),
        )


@dataclass(frozen=True)
class ArrayOverride:
    mode: ArrayOverrideMode
    values: tuple[Any, ...]

    def __post_init__(self) -> None:
        if self.mode not in {"replace", "append", "remove"}:
            raise PricingEngineError(f"Unsupported array override mode: {self.mode}")


@dataclass(frozen=True)
class CatalogItem:
    key: str
    plan_code: str
    prices: dict[str, Decimal | int | float | str | None]
    billing_period_days: int | None = None
    addons: tuple[str, ...] = ()
    billing_periods: tuple[int, ...] = ()
    availability: tuple[str, ...] = ()
    hidden: bool = False
    disabled: bool = False
    archived: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise PricingEngineError("Catalog item key is required")
        if not self.plan_code.strip():
            raise PricingEngineError("Catalog item plan_code is required")
        object.__setattr__(self, "prices", _normalize_prices(self.prices, allow_missing=True))


@dataclass(frozen=True)
class CatalogOverride:
    key: str
    scope: PricingScope
    item_key: str | None = None
    target: str | None = None
    targets: tuple[str, ...] = ()
    prices: dict[str, Decimal | int | float | str | None] = field(default_factory=dict)
    addons: ArrayOverride | None = None
    billing_periods: ArrayOverride | None = None
    availability: ArrayOverride | None = None
    hidden: bool | None = None
    disabled: bool | None = None
    archived: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.scope not in FALLBACK_ORDER:
            raise PricingEngineError(f"Unsupported pricing override scope: {self.scope}")
        if not self.key.strip():
            raise PricingEngineError("Catalog override key is required")
        object.__setattr__(self, "prices", _normalize_prices(self.prices, allow_missing=True))

    def matches(self, item: CatalogItem, context: PricingContext) -> bool:
        if self.item_key is not None and self.item_key != item.key:
            return False
        if self.scope == "global":
            return True

        context_value = _scope_context_value(self.scope, context)
        if context_value is None:
            return False

        targets = self.targets or ((self.target,) if self.target is not None else ())
        if not targets:
            return False
        return _normalize_scope_value(self.scope, context_value) in {
            _normalize_scope_value(self.scope, target) for target in targets
        }


@dataclass(frozen=True)
class EffectiveCatalogItem:
    key: str
    plan_code: str
    price: Decimal
    currency_code: str
    billing_period_days: int | None
    addons: tuple[str, ...]
    billing_periods: tuple[int, ...]
    availability: tuple[str, ...]
    hidden: bool
    disabled: bool
    archived: bool
    applied_override_keys: tuple[str, ...]
    metadata: dict[str, Any]

    @property
    def visible(self) -> bool:
        return not self.hidden and not self.disabled and not self.archived


@dataclass(frozen=True)
class EffectiveCatalog:
    context: PricingContext
    cache_key: str
    items: tuple[EffectiveCatalogItem, ...]
    invalidation_events: tuple[str, ...] = CATALOG_INVALIDATION_EVENTS


@dataclass(frozen=True)
class _ResolvedItemState:
    prices: dict[str, Decimal]
    addons: tuple[str, ...]
    billing_periods: tuple[int, ...]
    availability: tuple[str, ...]
    hidden: bool
    disabled: bool
    archived: bool
    metadata: dict[str, Any]
    applied_override_keys: tuple[str, ...]


class EffectiveCatalogResolver:
    def resolve(
        self,
        *,
        context: PricingContext,
        items: list[CatalogItem] | tuple[CatalogItem, ...],
        overrides: list[CatalogOverride] | tuple[CatalogOverride, ...] = (),
        catalog_version: str = "current",
        include_hidden: bool = False,
        include_disabled: bool = False,
        include_archived: bool = False,
    ) -> EffectiveCatalog:
        currency_code = _norm_currency(context.currency_code)
        effective_items: list[EffectiveCatalogItem] = []

        for item in items:
            state = self._resolve_item(item=item, context=context, overrides=tuple(overrides))
            if state.archived and not include_archived:
                continue
            if state.disabled and not include_disabled:
                continue
            if state.hidden and not include_hidden:
                continue

            price = state.prices.get(currency_code)
            if price is None:
                raise PricingEngineError(
                    f"Missing {currency_code} price for catalog item {item.key} after fallback resolution"
                )
            effective_items.append(
                EffectiveCatalogItem(
                    key=item.key,
                    plan_code=item.plan_code,
                    price=price,
                    currency_code=currency_code,
                    billing_period_days=item.billing_period_days,
                    addons=state.addons,
                    billing_periods=state.billing_periods,
                    availability=state.availability,
                    hidden=state.hidden,
                    disabled=state.disabled,
                    archived=state.archived,
                    applied_override_keys=state.applied_override_keys,
                    metadata=state.metadata,
                )
            )

        effective_items.sort(key=lambda resolved: (resolved.plan_code, resolved.billing_period_days or 0, resolved.key))
        return EffectiveCatalog(
            context=context,
            cache_key=build_catalog_cache_key(context=context, catalog_version=catalog_version),
            items=tuple(effective_items),
        )

    def _resolve_item(
        self,
        *,
        item: CatalogItem,
        context: PricingContext,
        overrides: tuple[CatalogOverride, ...],
    ) -> _ResolvedItemState:
        state = _ResolvedItemState(
            prices=dict(item.prices),
            addons=tuple(item.addons),
            billing_periods=tuple(item.billing_periods),
            availability=tuple(item.availability),
            hidden=item.hidden,
            disabled=item.disabled,
            archived=item.archived,
            metadata=dict(item.metadata),
            applied_override_keys=(),
        )

        for scope in FALLBACK_ORDER:
            for override in overrides:
                if override.scope != scope or not override.matches(item, context):
                    continue
                state = _apply_override(state, override)
        return state


def build_catalog_cache_key(
    *,
    context: PricingContext,
    catalog_version: str,
    namespace: str = "pricing:catalog",
) -> str:
    version = catalog_version.strip() or "current"
    fingerprint = sha256("|".join((version, *context.cache_parts())).encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:v1:{version}:{fingerprint}"


def _apply_override(state: _ResolvedItemState, override: CatalogOverride) -> _ResolvedItemState:
    prices = dict(state.prices)
    for currency, price in override.prices.items():
        normalized_currency = _norm_currency(currency)
        if price is None:
            prices.pop(normalized_currency, None)
        else:
            prices[normalized_currency] = _to_decimal(price)

    metadata = {**state.metadata, **override.metadata}

    return _ResolvedItemState(
        prices=prices,
        addons=_apply_array_override(state.addons, override.addons),
        billing_periods=_apply_array_override(state.billing_periods, override.billing_periods),
        availability=_apply_array_override(state.availability, override.availability),
        hidden=state.hidden if override.hidden is None else override.hidden,
        disabled=state.disabled if override.disabled is None else override.disabled,
        archived=state.archived if override.archived is None else override.archived,
        metadata=metadata,
        applied_override_keys=(*state.applied_override_keys, override.key),
    )


def _apply_array_override(current: tuple[Any, ...], override: ArrayOverride | None) -> tuple[Any, ...]:
    if override is None:
        return current
    if override.mode == "replace":
        return tuple(override.values)
    if override.mode == "append":
        merged = list(current)
        for value in override.values:
            if value not in merged:
                merged.append(value)
        return tuple(merged)
    if override.mode == "remove":
        removals = set(override.values)
        return tuple(value for value in current if value not in removals)
    raise PricingEngineError(f"Unsupported array override mode: {override.mode}")


def _normalize_prices(
    prices: dict[str, Decimal | int | float | str | None],
    *,
    allow_missing: bool,
) -> dict[str, Decimal | None]:
    normalized: dict[str, Decimal | None] = {}
    for currency, price in prices.items():
        normalized_currency = _norm_currency(currency)
        normalized[normalized_currency] = None if price is None else _to_decimal(price)
    if not allow_missing and not normalized:
        raise PricingEngineError("At least one price is required")
    return normalized


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PricingEngineError(f"Invalid catalog price: {value}") from exc
    if amount < 0:
        raise PricingEngineError("Catalog price cannot be negative")
    return amount


def _norm_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3:
        raise PricingEngineError(f"Invalid currency code: {value}")
    return normalized


def _norm_optional(value: str | None, *, upper: bool = False) -> str:
    if value is None:
        return "-"
    normalized = value.strip()
    if not normalized:
        return "-"
    return normalized.upper() if upper else normalized.lower()


def _scope_context_value(scope: PricingScope, context: PricingContext) -> str | None:
    return {
        "country_group": context.country_group,
        "country": context.country_code,
        "channel": context.channel,
        "partner": context.partner_key,
        "segment": context.segment,
        "promo": context.promo_code,
    }.get(scope)


def _normalize_scope_value(scope: PricingScope, value: str) -> str:
    upper_scopes = {"country_group", "country", "promo"}
    return value.strip().upper() if scope in upper_scopes else value.strip().lower()
