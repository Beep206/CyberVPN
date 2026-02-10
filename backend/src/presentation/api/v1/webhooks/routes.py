"""Webhook routes for external service callbacks."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.application.use_cases.webhooks.remnawave_webhook import ProcessRemnawaveWebhookUseCase
from src.config.settings import settings
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/remnawave", status_code=status.HTTP_200_OK)
async def remnawave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle webhook callbacks from Remnawave VPN service."""
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")

    validator = RemnawaveWebhookValidator(settings.remnawave_token.get_secret_value())
    use_case = ProcessRemnawaveWebhookUseCase(validator=validator, session=db)

    return await use_case.execute(body=body, signature=signature)


@router.post("/cryptobot", status_code=status.HTTP_200_OK)
async def cryptobot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle webhook callbacks from CryptoBot payment service."""
    body = await request.body()
    signature = request.headers.get("crypto-pay-api-signature", "")

    handler = CryptoBotWebhookHandler(settings.cryptobot_token.get_secret_value())
    use_case = ProcessPaymentWebhookUseCase(webhook_handler=handler, session=db)

    return await use_case.execute(provider="cryptobot", body=body, signature=signature)
