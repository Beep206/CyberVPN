from __future__ import annotations

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

    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="start")


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

    if not start_payload or start_payload.startswith(("auth_", "ref_", "promo_")):
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


async def _handle_start(
    message: Message,
    command: CommandObject,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext | None = None,
    user: dict[str, Any] | None = None,
    referrer_id: int | None = None,
    promo_code: str | None = None,
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

    # Check for magic link auth
    magic_auth_success = False
    if start_payload and start_payload.startswith("auth_"):
        token = start_payload.removeprefix("auth_")
        try:
            await api_client.complete_telegram_magic_link(
                token=token,
                telegram_id=user_id,
                first_name=first_name,
                last_name=last_name or None,
                username=username or None,
                language_code=language_code,
            )
            magic_auth_success = True
            logger.info("magic_link_auth_success", user_id=user_id, token_subset=token[:6])
        except APIError as exc:
            logger.warning(
                "magic_link_auth_failed",
                user_id=user_id,
                status_code=exc.status_code,
                detail=exc.detail,
            )
        if magic_auth_success:
            await message.answer(
                "<b>Success!</b>\nYou can return to the browser - sign-in completed automatically.",
                reply_markup=main_menu_keyboard(i18n),
            )
            logger.info("start_command_completed", user_id=user_id, flow="magic_link_auth")
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
                await message.answer(i18n.get("promo-activated", code=promo_code))
                logger.info("promo_activated_on_start", user_id=user_id, promo_code=promo_code)
            except Exception as e:
                logger.warning("promo_activation_failed", user_id=user_id, promo_code=promo_code, error=str(e))

    except Exception as e:
        logger.error("user_registration_failed", user_id=user_id, error=str(e))
        await message.answer(i18n.get("error-registration-failed"))
        return

    # Send welcome message with main menu
    welcome_text = i18n.get(
        "welcome-message" if is_new_user else "welcome-back",
        name=first_name or username or str(user_id),
    )

    if referrer_id:
        welcome_text += "\n\n" + i18n.get("welcome-referral-bonus")

    if magic_auth_success:
        welcome_text = (
            "<b>Success!</b>\nYou can return to the browser - sign-in completed automatically.\n\n" + welcome_text
        )

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
    )
