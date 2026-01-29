"""Webhook routes for external service callbacks."""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.webhooks.remnawave_webhook import ProcessRemnawaveWebhookUseCase
from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/remnawave", status_code=status.HTTP_200_OK)
async def remnawave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Handle webhook callbacks from Remnawave VPN service."""
    try:
        payload = await request.json()
        signature = request.headers.get("X-Webhook-Signature", "")

        validator = RemnawaveWebhookValidator()
        use_case = ProcessRemnawaveWebhookUseCase(validator=validator, session=db)

        result = await use_case.execute(payload=payload, signature=signature)

        return result
@router.post("/cryptobot", status_code=status.HTTP_200_OK)
async def cryptobot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Handle webhook callbacks from CryptoBot payment service."""
    try:
        payload = await request.json()
        signature = request.headers.get("crypto-pay-api-signature", "")

        handler = CryptoBotWebhookHandler()
        use_case = ProcessPaymentWebhookUseCase(handler=handler, session=db)

        result = await use_case.execute(payload=payload, signature=signature)

        return result