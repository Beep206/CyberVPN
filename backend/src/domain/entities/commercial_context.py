"""Locale, country and currency resolution contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_COUNTRY_CODE = "US"
DEFAULT_CURRENCY_CODE = "USD"
DEFAULT_UI_LOCALE = "en-US"

LANGUAGE_LOCALE_DEFAULTS: dict[str, str] = {
    "ar": "ar-SA",
    "be": "be-BY",
    "bn": "bn-BD",
    "cs": "cs-CZ",
    "de": "de-DE",
    "en": "en-US",
    "es": "es-ES",
    "fa": "fa-IR",
    "fil": "fil-PH",
    "fr": "fr-FR",
    "he": "he-IL",
    "hi": "hi-IN",
    "id": "id-ID",
    "it": "it-IT",
    "ja": "ja-JP",
    "kk": "kk-KZ",
    "ko": "ko-KR",
    "ms": "ms-MY",
    "my": "my-MM",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "pt": "pt-PT",
    "ro": "ro-RO",
    "ru": "ru-RU",
    "sv": "sv-SE",
    "th": "th-TH",
    "tr": "tr-TR",
    "uk": "uk-UA",
    "ur": "ur-PK",
    "uz": "uz-UZ",
    "vi": "vi-VN",
    "zh": "zh-CN",
}

LANGUAGE_COUNTRY_HINTS: dict[str, str] = {
    "ar": "SA",
    "be": "BY",
    "bn": "BD",
    "cs": "CZ",
    "de": "DE",
    "en": "US",
    "es": "ES",
    "fa": "IR",
    "fil": "PH",
    "fr": "FR",
    "he": "IL",
    "hi": "IN",
    "id": "ID",
    "it": "IT",
    "ja": "JP",
    "kk": "KZ",
    "ko": "KR",
    "ms": "MY",
    "my": "MM",
    "nl": "NL",
    "pl": "PL",
    "pt": "PT",
    "ro": "RO",
    "ru": "RU",
    "sv": "SE",
    "th": "TH",
    "tr": "TR",
    "uk": "UA",
    "ur": "PK",
    "uz": "UZ",
    "vi": "VN",
    "zh": "CN",
}

COUNTRY_CURRENCY_DEFAULTS: dict[str, str] = {
    "AU": "AUD",
    "BD": "BDT",
    "BE": "EUR",
    "BY": "BYN",
    "CA": "CAD",
    "CN": "CNY",
    "CZ": "CZK",
    "DE": "EUR",
    "ES": "EUR",
    "FR": "EUR",
    "GB": "GBP",
    "HU": "HUF",
    "ID": "IDR",
    "IL": "ILS",
    "IN": "INR",
    "IR": "IRR",
    "IT": "EUR",
    "JP": "JPY",
    "KR": "KRW",
    "KZ": "KZT",
    "MM": "MMK",
    "MY": "MYR",
    "NL": "EUR",
    "PH": "PHP",
    "PL": "PLN",
    "PT": "EUR",
    "RO": "RON",
    "RU": "RUB",
    "SA": "SAR",
    "SE": "SEK",
    "TH": "THB",
    "TR": "TRY",
    "UA": "UAH",
    "US": "USD",
    "UZ": "UZS",
    "VN": "VND",
}


@dataclass(frozen=True)
class CountryCurrencyOption:
    country_code: str
    default_currency_code: str
    supported_currency_codes: tuple[str, ...]
    payment_country_code: str | None = None
    locale_policy: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        country_code = normalize_country_code(self.country_code)
        default_currency = normalize_currency_code(self.default_currency_code)
        supported = tuple(dict.fromkeys(normalize_currency_code(code) for code in self.supported_currency_codes))
        if default_currency not in supported:
            raise ValueError("default_currency_code must be present in supported_currency_codes")
        payment_country = normalize_country_code(self.payment_country_code) if self.payment_country_code else None
        object.__setattr__(self, "country_code", country_code)
        object.__setattr__(self, "default_currency_code", default_currency)
        object.__setattr__(self, "supported_currency_codes", supported)
        object.__setattr__(self, "payment_country_code", payment_country)


@dataclass(frozen=True)
class CurrencyOption:
    currency_code: str
    minor_units: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency_code", normalize_currency_code(self.currency_code))


@dataclass(frozen=True)
class CommercialContextSignals:
    url_locale: str | None = None
    browser_language: str | None = None
    telegram_language_code: str | None = None
    explicit_ui_locale: str | None = None
    explicit_display_country_code: str | None = None
    explicit_pricing_country_code: str | None = None
    explicit_currency_code: str | None = None
    session_country_code: str | None = None
    session_currency_code: str | None = None
    cookie_country_code: str | None = None
    cookie_currency_code: str | None = None
    profile_ui_locale: str | None = None
    profile_display_country_code: str | None = None
    profile_pricing_country_code: str | None = None
    profile_currency_code: str | None = None
    channel_key: str | None = None
    channel_default_locale: str | None = None
    fallback_country_code: str = DEFAULT_COUNTRY_CODE


@dataclass(frozen=True)
class ResolvedCommercialContext:
    ui_locale: str
    display_country: str
    pricing_country: str
    payment_country: str
    currency: str
    confidence: str
    selectable_countries: tuple[str, ...]
    selectable_currencies: tuple[str, ...]
    resolution_trace: tuple[str, ...]


def resolve_commercial_context(
    signals: CommercialContextSignals,
    *,
    country_options: list[CountryCurrencyOption],
    currency_options: list[CurrencyOption],
) -> ResolvedCommercialContext:
    countries = _options_by_country(country_options)
    currencies = {option.currency_code for option in currency_options}
    if not countries:
        fallback_country = _safe_country(signals.fallback_country_code)
        fallback_currency = COUNTRY_CURRENCY_DEFAULTS.get(fallback_country, DEFAULT_CURRENCY_CODE)
        countries = {
            fallback_country: CountryCurrencyOption(
                country_code=fallback_country,
                default_currency_code=fallback_currency,
                supported_currency_codes=(fallback_currency,),
            )
        }
    if not currencies:
        currencies = {currency for option in countries.values() for currency in option.supported_currency_codes}

    trace: list[str] = []
    ui_locale, ui_source = _resolve_ui_locale(signals)
    trace.append(ui_source)

    display_country, display_source = _first_country(
        (
            ("explicit_display_country", signals.explicit_display_country_code),
            ("profile_display_country", signals.profile_display_country_code),
            ("session_country", signals.session_country_code),
            ("cookie_country", signals.cookie_country_code),
            ("url_locale_country", extract_country_from_locale(signals.url_locale)),
            ("telegram_language_country", country_from_language(signals.telegram_language_code)),
            ("browser_language_country", extract_country_from_accept_language(signals.browser_language)),
            ("fallback_country", signals.fallback_country_code),
        ),
        countries,
    )
    trace.append(display_source)

    pricing_country, pricing_source = _first_country(
        (
            ("explicit_pricing_country", signals.explicit_pricing_country_code),
            ("profile_pricing_country", signals.profile_pricing_country_code),
            ("pricing_from_display_country", display_country),
        ),
        countries,
    )
    trace.append(pricing_source)
    country_option = countries[pricing_country]

    currency, currency_source = _resolve_currency(
        signals=signals,
        country_option=country_option,
        active_currency_codes=currencies,
        strict_explicit=signals.explicit_currency_code is not None,
    )
    trace.append(currency_source)

    selectable_currencies = tuple(
        sorted(currency for currency in country_option.supported_currency_codes if currency in currencies)
    )
    return ResolvedCommercialContext(
        ui_locale=ui_locale,
        display_country=display_country,
        pricing_country=pricing_country,
        payment_country=country_option.payment_country_code or pricing_country,
        currency=currency,
        confidence=_confidence_from_sources(display_source, pricing_source, currency_source),
        selectable_countries=tuple(sorted(countries)),
        selectable_currencies=selectable_currencies,
        resolution_trace=tuple(trace),
    )


def normalize_country_code(value: str | None) -> str:
    if value is None:
        raise ValueError("country code is required")
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("country code must be a 2-letter ISO code")
    return normalized


def normalize_currency_code(value: str | None) -> str:
    if value is None:
        raise ValueError("currency code is required")
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("currency code must be a 3-letter ISO code")
    return normalized


def normalize_locale(value: str | None) -> str | None:
    if value is None:
        return None
    tag = value.strip().replace("_", "-")
    if not tag:
        return None
    parts = [part for part in tag.split("-") if part]
    if not parts:
        return None
    language = parts[0].lower()
    if not language.isalpha() or len(language) < 2:
        return None
    if len(parts) == 1:
        return LANGUAGE_LOCALE_DEFAULTS.get(language, language)
    region = parts[1].upper()
    if len(region) == 2 and region.isalpha():
        return f"{language}-{region}"
    return LANGUAGE_LOCALE_DEFAULTS.get(language, language)


def extract_country_from_locale(value: str | None) -> str | None:
    locale = normalize_locale(value)
    if not locale or "-" not in locale:
        return None
    region = locale.split("-", 1)[1]
    if len(region) == 2 and region.isalpha():
        return region.upper()
    return None


def country_from_language(value: str | None) -> str | None:
    locale = normalize_locale(value)
    if not locale:
        return None
    language = locale.split("-", 1)[0]
    return LANGUAGE_COUNTRY_HINTS.get(language)


def extract_country_from_accept_language(value: str | None) -> str | None:
    locale = first_accept_language(value)
    return extract_country_from_locale(locale) or country_from_language(locale)


def first_accept_language(value: str | None) -> str | None:
    if value is None:
        return None
    candidates: list[tuple[float, str]] = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        language_range, _, raw_quality = part.partition(";")
        quality = 1.0
        if raw_quality.strip().startswith("q="):
            try:
                quality = float(raw_quality.strip()[2:])
            except ValueError:
                quality = 0.0
        if language_range.strip() != "*":
            candidates.append((quality, language_range.strip()))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _options_by_country(options: list[CountryCurrencyOption]) -> dict[str, CountryCurrencyOption]:
    return {option.country_code: option for option in options}


def _resolve_ui_locale(signals: CommercialContextSignals) -> tuple[str, str]:
    for source, raw_locale in (
        ("explicit_ui_locale", signals.explicit_ui_locale),
        ("profile_ui_locale", signals.profile_ui_locale),
        ("url_locale", signals.url_locale),
        ("telegram_language_locale", signals.telegram_language_code),
        ("browser_language_locale", first_accept_language(signals.browser_language)),
        ("channel_default_locale", signals.channel_default_locale),
        ("fallback_ui_locale", DEFAULT_UI_LOCALE),
    ):
        locale = normalize_locale(raw_locale)
        if locale:
            return locale, source
    return DEFAULT_UI_LOCALE, "fallback_ui_locale"


def _first_country(
    candidates: tuple[tuple[str, str | None], ...],
    countries: dict[str, CountryCurrencyOption],
) -> tuple[str, str]:
    fallback = next(iter(countries))
    for source, raw_country in candidates:
        if raw_country is None:
            continue
        try:
            country = normalize_country_code(raw_country)
        except ValueError:
            continue
        if country in countries:
            return country, source
    return fallback, "fallback_configured_country"


def _resolve_currency(
    *,
    signals: CommercialContextSignals,
    country_option: CountryCurrencyOption,
    active_currency_codes: set[str],
    strict_explicit: bool,
) -> tuple[str, str]:
    for source, raw_currency in (
        ("explicit_currency", signals.explicit_currency_code),
        ("profile_currency", signals.profile_currency_code),
        ("session_currency", signals.session_currency_code),
        ("cookie_currency", signals.cookie_currency_code),
    ):
        if raw_currency is None:
            continue
        currency = normalize_currency_code(raw_currency)
        if currency not in active_currency_codes:
            if strict_explicit and source == "explicit_currency":
                raise ValueError("Explicit currency is not active")
            continue
        if currency not in country_option.supported_currency_codes:
            if strict_explicit and source == "explicit_currency":
                raise ValueError("Explicit currency is not selectable for pricing country")
            continue
        return currency, source
    return country_option.default_currency_code, "country_default_currency"


def _confidence_from_sources(display_source: str, pricing_source: str, currency_source: str) -> str:
    sources = {display_source, pricing_source, currency_source}
    if any(source.startswith("explicit_") for source in sources):
        return "explicit"
    if any(
        source.startswith("profile_") or source.startswith("session_") or source.startswith("cookie_")
        for source in sources
    ):
        return "high"
    if any(
        source.startswith("url_") or source.startswith("telegram_") or source.startswith("browser_")
        for source in sources
    ):
        return "medium"
    return "low"


def _safe_country(value: str) -> str:
    try:
        return normalize_country_code(value)
    except ValueError:
        return DEFAULT_COUNTRY_CODE
