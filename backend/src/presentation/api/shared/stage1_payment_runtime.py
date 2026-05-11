"""Stage 1 payment runtime gates.

These guards are intentionally runtime-config driven: the deploy can pause new
paid flows without rebuilding images, while reconciliation/status routes remain
available for support and orphan-payment handling.
"""

from fastapi import HTTPException, status

from src.config.settings import settings

PAYMENTS_DISABLED_DETAIL = "Payments are temporarily unavailable during Stage 1 rollout."
TELEGRAM_STARS_DISABLED_DETAIL = "Telegram Stars checkout is disabled until Stage 1 evidence is approved."


def require_stage1_payments_enabled() -> None:
    """Block new paid checkout/invoice creation when the S1 kill switch is off."""

    if settings.payments_enabled:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=PAYMENTS_DISABLED_DETAIL,
    )


def require_stage1_telegram_stars_enabled() -> None:
    """Block new Telegram Stars invoices unless both S1 payment gates are open."""

    require_stage1_payments_enabled()
    if settings.telegram_stars_enabled:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=TELEGRAM_STARS_DISABLED_DETAIL,
    )
