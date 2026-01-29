from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="trial")


@router.callback_query(F.data == "trial:activate")
async def activate_trial_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Activate trial subscription."""
    user_id = callback.from_user.id

    try:
        # Check trial eligibility
        eligibility = await api_client.check_trial_eligibility(user_id)

        if not eligibility.get("eligible", False):
            reason = eligibility.get("reason", "unknown")
            await callback.answer(
                i18n.get(f"trial-not-eligible-{reason}"),
                show_alert=True,
            )
            return

        # Activate trial
        trial = await api_client.activate_trial(user_id)

        trial_duration = trial.get("duration_days", 3)
        expires_at = trial.get("expires_at", "N/A")

        await callback.message.edit_text(
            text=i18n.get(
                "trial-activated",
                duration=trial_duration,
                expires=expires_at,
            ),
        )

        # Show config delivery options
        from keyboards.config import config_delivery_keyboard

        await callback.message.answer(
            text=i18n.get("config-delivery-prompt"),
            reply_markup=config_delivery_keyboard(i18n),
        )

        logger.info("trial_activated", user_id=user_id, trial_id=trial.get("id"))

    except Exception as e:
        logger.error("trial_activation_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-trial-activation-failed"), show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "trial:check")
async def check_trial_eligibility_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Check trial eligibility."""
    user_id = callback.from_user.id

    try:
        eligibility = await api_client.check_trial_eligibility(user_id)

        if eligibility.get("eligible", False):
            await callback.answer(
                i18n.get("trial-eligible"),
                show_alert=True,
            )
        else:
            reason = eligibility.get("reason", "unknown")
            await callback.answer(
                i18n.get(f"trial-not-eligible-{reason}"),
                show_alert=True,
            )

        logger.info("trial_eligibility_checked", user_id=user_id, eligible=eligibility.get("eligible"))

    except Exception as e:
        logger.error("trial_eligibility_check_error", user_id=user_id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
