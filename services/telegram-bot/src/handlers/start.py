from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import structlog
from aiogram import Router
from aiogram.filters import CommandObject, CommandStart

from src.handlers.subscription import present_explicit_plan_offer
from src.keyboards.menu import main_menu_keyboard
from src.services.api_client import APIError
from src.utils.deep_links import decode_deep_link

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient
    from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)

router = Router(name="start")

AUTH_LINK_PREFIX = "auth_"
ACCOUNT_LINK_PREFIX = "link_"
LEGACY_LOGIN_LINK_PREFIX = "login_"
AUTH_LINK_PAYLOAD_PREFIXES = (AUTH_LINK_PREFIX, ACCOUNT_LINK_PREFIX, LEGACY_LOGIN_LINK_PREFIX)
CONNECTION_START_PAYLOADS = {"connect", "connection", "vpn"}
ONBOARDING_LINK_PREFIX = "onboarding_"
CODE_LINK_PREFIX = "code_"


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def _account_link_message_key_for_error(exc: APIError) -> str:
    if exc.status_code == 404:
        return "telegram-account-link-expired"
    if exc.status_code == 409:
        return "telegram-account-link-conflict"
    if exc.status_code == 429:
        return "telegram-account-link-rate-limited"
    if exc.status_code in {401, 403}:
        return "telegram-account-link-service-unavailable"
    return "telegram-account-link-service-unavailable"


def _get_start_payload(message: Message, command: CommandObject) -> str | None:
    """Extract the /start payload from CommandObject or raw message text."""
    if command.args:
        return command.args.strip() or None

    text = (message.text or "").strip()
    if not text.startswith("/start"):
        return None

    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        payload = parts[1].strip()
        return payload or None
    return None


def _parse_subscription_offer_payload(start_payload: str | None) -> dict[str, Any] | None:
    """Decode signed subscription deep links created by utils.deep_links."""

    if not start_payload or start_payload.startswith((*AUTH_LINK_PAYLOAD_PREFIXES, "ref_", "promo_")):
        return None

    try:
        payload = decode_deep_link(start_payload)
    except ValueError:
        return None

    if str(payload.get("type") or "") != "subscribe":
        return None

    plan_id = str(payload.get("plan") or "").strip()
    if not plan_id:
        return None

    duration_days: int | None = None
    raw_days = payload.get("days")
    if raw_days is not None:
        try:
            duration_days = int(raw_days)
        except (TypeError, ValueError):
            duration_days = None

    return {"plan_id": plan_id, "duration_days": duration_days}


def _is_auth_magic_link_payload(start_payload: str | None) -> bool:
    return bool(start_payload and start_payload.startswith(AUTH_LINK_PREFIX))


def _is_account_link_payload(start_payload: str | None) -> bool:
    return bool(start_payload and start_payload.startswith(ACCOUNT_LINK_PREFIX))


def _is_legacy_login_link_payload(start_payload: str | None) -> bool:
    return bool(start_payload and start_payload.startswith(LEGACY_LOGIN_LINK_PREFIX))


def _is_connection_start_payload(start_payload: str | None) -> bool:
    if not start_payload:
        return False
    return start_payload in CONNECTION_START_PAYLOADS or start_payload.startswith(ONBOARDING_LINK_PREFIX)


def _extract_code_start_payload(start_payload: str | None) -> str | None:
    if not start_payload or not start_payload.startswith(CODE_LINK_PREFIX):
        return None
    code = start_payload.removeprefix(CODE_LINK_PREFIX).strip()
    return code or None


async def _handle_start(
    message: Message,
    command: CommandObject,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext | None = None,
    user: dict[str, Any] | None = None,
    referrer_id: int | None = None,
    promo_code: str | None = None,
    cache: CacheService | None = None,
    settings: BotSettings | None = None,
) -> None:
    """Handle /start command with deep link support."""
    if message.from_user is None:
        return

    is_new_user = user is None
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    language_code = message.from_user.language_code or "en"
    start_payload = _get_start_payload(message, command)
    direct_offer = _parse_subscription_offer_payload(start_payload)
    code_payload = _extract_code_start_payload(start_payload)

    if _is_account_link_payload(start_payload):
        token = (start_payload or "").removeprefix(ACCOUNT_LINK_PREFIX).strip()
        if not token:
            await message.answer(i18n.get("telegram-account-link-expired"))
            logger.warning("account_link_empty_token", user_id=user_id)
            return

        try:
            await api_client.complete_telegram_account_link(
                token=token,
                telegram_id=user_id,
                first_name=first_name,
                last_name=last_name or None,
                username=username or None,
                language_code=language_code,
            )
        except APIError as exc:
            logger.warning(
                "account_link_failed",
                user_id=user_id,
                status_code=exc.status_code,
                detail=exc.detail,
                token_fingerprint=_token_fingerprint(token),
            )
            await message.answer(i18n.get(_account_link_message_key_for_error(exc)))
            logger.info("start_command_completed", user_id=user_id, flow="account_link", status="failed")
            return

        await message.answer(i18n.get("telegram-account-link-success"))
        logger.info(
            "account_link_success",
            user_id=user_id,
            token_fingerprint=_token_fingerprint(token),
        )
        logger.info("start_command_completed", user_id=user_id, flow="account_link")
        return

    if _is_auth_magic_link_payload(start_payload):
        token = (start_payload or "").removeprefix(AUTH_LINK_PREFIX).strip()
        if not token:
            await message.answer(i18n.get("telegram-auth-link-invalid"))
            logger.warning("magic_link_auth_missing_token", user_id=user_id)
            return

        try:
            await api_client.complete_telegram_magic_link(
                token=token,
                telegram_id=user_id,
                first_name=first_name,
                last_name=last_name or None,
                username=username or None,
                language_code=language_code,
            )
            logger.info("magic_link_auth_success", user_id=user_id, token_subset=token[:6])
        except APIError as exc:
            logger.warning(
                "magic_link_auth_failed",
                user_id=user_id,
                status_code=exc.status_code,
                detail=exc.detail,
                token_fingerprint=_token_fingerprint(token),
            )
            await message.answer(
                i18n.get("telegram-auth-link-invalid"),
            )
            return

        await message.answer(
            i18n.get("telegram-auth-link-success"),
            reply_markup=main_menu_keyboard(i18n),
        )
        logger.info("start_command_completed", user_id=user_id, flow="magic_link_auth")
        return

    if _is_legacy_login_link_payload(start_payload):
        await message.answer(i18n.get("telegram-auth-link-legacy-unsupported"))
        logger.info("start_command_completed", user_id=user_id, flow="legacy_login_link_unsupported")
        return

    # Update user data on /start and ensure registration exists
    try:
        if user is None:
            user = await api_client.register_user(
                telegram_id=user_id,
                username=username or None,
                first_name=first_name or None,
                language=language_code,
                referrer_id=referrer_id,
            )
            logger.info("user_registered", user_id=user_id, user=user)
        else:
            await api_client.update_user(
                user_id,
                {
                    "username": username or None,
                    "language": language_code,
                },
            )

        # Auto-activate promo code if provided
        if promo_code:
            try:
                await api_client.activate_promocode(user_id, promo_code)
                from src.handlers.connection import code_fingerprint, mask_code

                await message.answer(i18n.get("promo-activated", code=mask_code(promo_code)))
                logger.info(
                    "promo_activated_on_start",
                    user_id=user_id,
                    promo_code_fingerprint=code_fingerprint(promo_code),
                )
            except Exception as e:
                from src.handlers.connection import code_fingerprint

                logger.warning(
                    "promo_activation_failed",
                    user_id=user_id,
                    promo_code_fingerprint=code_fingerprint(promo_code),
                    error_type=type(e).__name__,
                )

    except Exception as e:
        logger.error("user_registration_failed", user_id=user_id, error=str(e))
        await message.answer(i18n.get("error-registration-failed"))
        return

    if cache is not None and code_payload is not None:
        from src.handlers.connection import apply_code_and_open_connection, code_fingerprint

        await apply_code_and_open_connection(
            message,
            i18n,
            api_client,
            cache,
            settings,
            code=code_payload,
        )
        logger.info(
            "start_command_completed",
            user_id=user_id,
            flow="connection_code",
            code_fingerprint=code_fingerprint(code_payload),
        )
        return

    if cache is not None and _is_connection_start_payload(start_payload):
        from src.handlers.connection import open_connection_from_message

        await open_connection_from_message(message, i18n, api_client, cache, settings)
        logger.info("start_command_completed", user_id=user_id, flow="connection")
        return

    # Send welcome message with main menu
    welcome_text = i18n.get(
        "welcome-message" if is_new_user else "welcome-back",
        name=first_name or username or str(user_id),
    )

    if referrer_id:
        welcome_text += "\n\n" + i18n.get("welcome-referral-bonus")

    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_keyboard(i18n),
    )

    if direct_offer and state is not None:
        try:
            plan = await api_client.get_plan(direct_offer["plan_id"])
            offer_started = await present_explicit_plan_offer(
                state=state,
                i18n=i18n,
                plan=plan,
                target_message=message,
                requested_duration_days=direct_offer.get("duration_days"),
            )
            if offer_started:
                logger.info(
                    "start_direct_offer_opened",
                    user_id=user_id,
                    plan_id=direct_offer["plan_id"],
                    duration_days=direct_offer.get("duration_days"),
                )
            else:
                await message.answer(i18n.get("subscription-hidden-plan-unavailable"))
        except Exception as exc:
            logger.warning(
                "start_direct_offer_failed",
                user_id=user_id,
                plan_id=direct_offer["plan_id"],
                error=str(exc),
            )
            await message.answer(i18n.get("subscription-hidden-plan-unavailable"))

    logger.info("start_command_completed", user_id=user_id)


@router.message(CommandStart(deep_link=True))
async def start_with_deep_link_handler(
    message: Message,
    command: CommandObject,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext | None = None,
    user: dict[str, Any] | None = None,
    referrer_id: int | None = None,
    promo_code: str | None = None,
    cache: CacheService | None = None,
    settings: BotSettings | None = None,
) -> None:
    await _handle_start(
        message=message,
        command=command,
        i18n=i18n,
        api_client=api_client,
        state=state,
        user=user,
        referrer_id=referrer_id,
        promo_code=promo_code,
        cache=cache,
        settings=settings,
    )


# aiogram 3.27 changed the default deep_link behavior to "accept both";
# keep plain /start explicit so auth/referral payloads stay on the deep-link route.
@router.message(CommandStart(deep_link=False))
async def start_handler(
    message: Message,
    command: CommandObject,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext | None = None,
    user: dict[str, Any] | None = None,
    referrer_id: int | None = None,
    promo_code: str | None = None,
    cache: CacheService | None = None,
    settings: BotSettings | None = None,
) -> None:
    await _handle_start(
        message=message,
        command=command,
        i18n=i18n,
        api_client=api_client,
        state=state,
        user=user,
        referrer_id=referrer_id,
        promo_code=promo_code,
        cache=cache,
        settings=settings,
    )
