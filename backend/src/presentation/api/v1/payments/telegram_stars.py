"""Helpers for authenticated Telegram Stars checkout flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository


@dataclass(frozen=True)
class TelegramStarsCheckoutResult:
    payment: PaymentModel
    invoice_url: str
    expires_at: datetime
    stars_amount: int


def extract_telegram_stars_amount(features: dict[str, Any] | None) -> int | None:
    """Resolve Telegram Stars amount from plan features."""
    if not isinstance(features, dict):
        return None

    direct = features.get("telegram_stars_amount")
    nested = features.get("telegram_stars")
    prices = features.get("prices")
    candidates = [
        direct,
        nested.get("amount") if isinstance(nested, dict) else None,
        prices.get("XTR") if isinstance(prices, dict) else None,
    ]

    for candidate in candidates:
        if candidate in (None, ""):
            continue
        try:
            value = int(candidate)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value

    return None


def build_telegram_stars_invoice_payload(*, payment_id: str, telegram_id: int) -> str:
    return f"stars:{payment_id}:{telegram_id}"


async def create_telegram_stars_checkout(
    session: AsyncSession,
    *,
    user: MobileUserModel,
    quote_result,
    channel: str,
    checkout_mode: str,
    description: str,
) -> TelegramStarsCheckoutResult:
    """Create a pending Telegram Stars payment and invoice link for Mini App checkout."""
    if user.telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram Stars checkout requires a Telegram-linked account",
        )

    if quote_result.plan_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram Stars checkout requires a plan-based purchase",
        )

    plan = await SubscriptionPlanRepository(session).get_by_id(quote_result.plan_id)
    stars_amount = extract_telegram_stars_amount(plan.features if plan is not None else None)
    if stars_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram Stars pricing is not configured for this plan",
        )

    payment_repo = PaymentRepository(session)
    payment = await payment_repo.create(
        PaymentModel(
            external_id=None,
            user_uuid=user.id,
            amount=float(stars_amount),
            currency="XTR",
            status="pending",
            provider="telegram_stars",
            subscription_days=quote_result.duration_days or 0,
            plan_id=quote_result.plan_id,
            promo_code_id=quote_result.promo_code_id,
            partner_code_id=quote_result.partner_code_id,
            discount_amount=float(quote_result.discount_amount),
            wallet_amount_used=0,
            final_amount=float(stars_amount),
            addons_snapshot=[
                {
                    "addon_id": str(line.addon_id),
                    "code": line.code,
                    "qty": line.qty,
                    "unit_price": float(line.unit_price),
                    "total_price": float(line.total_price),
                    "location_code": line.location_code,
                    "delta_entitlements": line.delta_entitlements,
                }
                for line in quote_result.addons
            ],
            entitlements_snapshot=quote_result.entitlements_snapshot,
            metadata_={
                "commission_base_amount": str(quote_result.commission_base_amount),
                "addon_amount": str(quote_result.addon_amount),
                "channel": channel,
                "plan_name": quote_result.plan_name,
                "checkout_mode": checkout_mode,
                "telegram_stars_amount": stars_amount,
                "displayed_price_usd": str(quote_result.displayed_price),
                "quote_currency": "XTR",
            },
        )
    )

    invoice_payload = build_telegram_stars_invoice_payload(payment_id=str(payment.id), telegram_id=user.telegram_id)
    invoice_url = await _create_telegram_invoice_link(
        title=(quote_result.plan_name or "CyberVPN subscription")[:32],
        description=description[:255],
        invoice_payload=invoice_payload,
        stars_amount=stars_amount,
    )

    payment.metadata_ = {
        **(payment.metadata_ or {}),
        "invoice_payload": invoice_payload,
        "invoice_url": invoice_url,
    }
    await payment_repo.update(payment)

    return TelegramStarsCheckoutResult(
        payment=payment,
        invoice_url=invoice_url,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
        stars_amount=stars_amount,
    )


async def _create_telegram_invoice_link(
    *,
    title: str,
    description: str,
    invoice_payload: str,
    stars_amount: int,
) -> str:
    token = settings.telegram_bot_token.get_secret_value().strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot token is not configured",
        )

    request_payload = {
        "title": title,
        "description": description,
        "payload": invoice_payload,
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": title, "amount": stars_amount}],
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        try:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/createInvoiceLink",
                json=request_payload,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Telegram invoice creation failed: {exc}",
            ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Telegram invoice creation returned invalid JSON",
        ) from exc

    if response.status_code >= 400 or not payload.get("ok") or not isinstance(payload.get("result"), str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(payload.get("description") or "Telegram invoice creation failed"),
        )

    return payload["result"]
