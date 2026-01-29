"""CyberVPN Telegram Bot — Fluent i18n middleware.

Determines user language and injects a Fluent translator function
into handler data for localized message formatting.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from fluent.runtime import FluentBundle, FluentResource

logger = structlog.get_logger(__name__)

# Supported locale codes
SUPPORTED_LOCALES = ("ru", "en")
DEFAULT_LOCALE = "ru"

# Telegram language_code → our locale mapping
LANGUAGE_MAP: dict[str, str] = {
    "ru": "ru",
    "uk": "ru",  # Ukrainian → Russian fallback
    "be": "ru",  # Belarusian → Russian fallback
    "kk": "ru",  # Kazakh → Russian fallback
    "en": "en",
    "en-US": "en",
    "en-GB": "en",
}


class FluentTranslator:
    """Wrapper around FluentBundle providing a callable translator interface.

    Usage in handlers:
        i18n = data['i18n']
        text = i18n('welcome', name="User")
    """

    def __init__(
        self,
        bundle: FluentBundle,
        fallback_bundle: FluentBundle | None = None,
    ) -> None:
        self._bundle = bundle
        self._fallback = fallback_bundle

    def __call__(self, key: str, **kwargs: Any) -> str:
        """Translate a message key with optional variables.

        Args:
            key: Fluent message identifier.
            **kwargs: Variables to interpolate into the message.

        Returns:
            Translated string, or key name if translation is missing.
        """
        result = self._format(self._bundle, key, kwargs)
        if result is not None:
            return result

        # Fallback to default locale
        if self._fallback is not None:
            result = self._format(self._fallback, key, kwargs)
            if result is not None:
                return result

        logger.warning("missing_translation", key=key)
        return key

    @staticmethod
    def _format(
        bundle: FluentBundle,
        key: str,
        args: dict[str, Any],
    ) -> str | None:
        """Attempt to format a message from a bundle."""
        if not bundle.has_message(key):
            return None
        message = bundle.format(key, args)
        # FluentBundle.format returns (value, errors) tuple
        if isinstance(message, tuple):
            return message[0]
        return message


class I18nManager:
    """Manages Fluent bundles for all supported locales.

    Loads .ftl files from the locales directory at initialization
    and caches FluentBundle instances per locale.
    """

    def __init__(self, locales_dir: str | Path | None = None) -> None:
        if locales_dir is None:
            locales_dir = Path(__file__).parent.parent / "locales"
        self._locales_dir = Path(locales_dir)
        self._bundles: dict[str, FluentBundle] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all .ftl files for all supported locales."""
        for locale in SUPPORTED_LOCALES:
            locale_dir = self._locales_dir / locale
            if not locale_dir.is_dir():
                logger.warning("locale_directory_missing", locale=locale)
                continue

            bundle = FluentBundle([locale])
            ftl_files = sorted(locale_dir.glob("*.ftl"))

            for ftl_path in ftl_files:
                content = ftl_path.read_text(encoding="utf-8")
                resource = FluentResource(content)
                bundle.add_resource(resource)

            self._bundles[locale] = bundle
            logger.info(
                "locale_loaded",
                locale=locale,
                files=len(ftl_files),
            )

    def get_bundle(self, locale: str) -> FluentBundle | None:
        """Get FluentBundle for a locale."""
        return self._bundles.get(locale)

    def get_translator(self, locale: str) -> FluentTranslator:
        """Get a translator for the given locale with fallback.

        Args:
            locale: Target locale code.

        Returns:
            FluentTranslator with optional fallback to default locale.
        """
        bundle = self.get_bundle(locale)
        fallback = (
            self.get_bundle(DEFAULT_LOCALE)
            if locale != DEFAULT_LOCALE
            else None
        )

        if bundle is None:
            bundle = self.get_bundle(DEFAULT_LOCALE)
            if bundle is None:
                msg = f"Default locale '{DEFAULT_LOCALE}' bundle not found"
                raise RuntimeError(msg)
            fallback = None

        return FluentTranslator(bundle=bundle, fallback_bundle=fallback)


# Module-level singleton (initialized on first import)
_i18n_manager: I18nManager | None = None


def get_i18n_manager() -> I18nManager:
    """Get or create the singleton I18nManager."""
    global _i18n_manager  # noqa: PLW0603
    if _i18n_manager is None:
        locales_dir = os.environ.get("I18N_LOCALES_DIR")
        _i18n_manager = I18nManager(locales_dir)
    return _i18n_manager


class I18nMiddleware(BaseMiddleware):
    """Middleware that injects i18n translator into handler data.

    Language detection priority:
    1. User's saved language preference (from data['user'] if available)
    2. Telegram's language_code from the user object
    3. DEFAULT_LOCALE fallback

    Injects into handler data:
    - data['i18n'] — FluentTranslator callable
    - data['locale'] — resolved locale string (e.g., 'ru', 'en')
    """

    def __init__(self, i18n_manager: I18nManager | None = None) -> None:
        self._manager = i18n_manager or get_i18n_manager()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Resolve locale and inject translator.

        Args:
            handler: Next handler in the chain.
            event: Telegram event.
            data: Handler data dict.

        Returns:
            Result from the next handler.
        """
        locale = self._resolve_locale(event, data)
        translator = self._manager.get_translator(locale)

        data["i18n"] = translator
        data["locale"] = locale

        return await handler(event, data)

    @staticmethod
    def _resolve_locale(event: TelegramObject, data: dict[str, Any]) -> str:
        """Determine locale from available context.

        Priority: user DB preference → Telegram language → default.
        """
        # 1. Check user's saved preference
        user = data.get("user")
        if user is not None and hasattr(user, "language"):
            lang = getattr(user, "language", None)
            if lang and lang in SUPPORTED_LOCALES:
                return lang

        # 2. Check Telegram language_code
        tg_user = None
        if isinstance(event, Message) and event.from_user:
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            tg_user = event.from_user

        if tg_user and tg_user.language_code:
            lang_code = tg_user.language_code
            mapped = LANGUAGE_MAP.get(lang_code)
            if mapped:
                return mapped
            # Try base language (e.g., "pt-BR" → "pt")
            base = lang_code.split("-")[0]
            mapped = LANGUAGE_MAP.get(base)
            if mapped:
                return mapped

        # 3. Default
        return DEFAULT_LOCALE
