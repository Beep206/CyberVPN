"""Webhook routes for external service callbacks."""

import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.payments.payment_webhook import ProcessPaymentWebhookUseCase
from src.application.use_cases.webhooks.remnawave_webhook import ProcessRemnawaveWebhookUseCase
from src.config.settings import settings
from src.domain.exceptions.domain_errors import InvalidWebhookSignatureError
from src.infrastructure.monitoring.metrics import webhook_operations_total
from src.infrastructure.payments.cryptobot.webhook_handler import CryptoBotWebhookHandler
from src.infrastructure.remnawave.webhook_validator import RemnawaveWebhookValidator
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider
from src.presentation.api.shared.stage1_webhook_signature import verify_stage1_webhook_signature
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)
_webhook_secret_fallback_warned = False


@router.post("/remnawave", status_code=status.HTTP_200_OK)
async def remnawave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle webhook callbacks from Remnawave VPN service."""
    global _webhook_secret_fallback_warned

    body = await request.body()
    signature = request.headers.get("X-Remnawave-Signature") or request.headers.get("X-Webhook-Signature")
    timestamp = request.headers.get("X-Remnawave-Timestamp")
    allow_missing_timestamp = bool(request.headers.get("X-Webhook-Signature")) and not bool(
        request.headers.get("X-Remnawave-Signature")
    )

    webhook_secret = settings.remnawave_webhook_secret.get_secret_value() or settings.remnawave_token.get_secret_value()
    if not settings.remnawave_webhook_secret.get_secret_value() and not _webhook_secret_fallback_warned:
        logger.warning("REMNAWAVE_WEBHOOK_SECRET is not configured; falling back to REMNAWAVE_TOKEN for validation")
        _webhook_secret_fallback_warned = True

    validator = RemnawaveWebhookValidator(
        webhook_secret,
        max_age_seconds=settings.remnawave_webhook_max_age_seconds,
        future_skew_seconds=settings.remnawave_webhook_future_skew_seconds,
    )
    use_case = ProcessRemnawaveWebhookUseCase(validator=validator, session=db)

    result = await use_case.execute(
        body=body,
        signature=signature,
        timestamp=timestamp,
        allow_missing_timestamp=allow_missing_timestamp,
    )
    webhook_operations_total.labels(provider="remnawave", status=result.get("status", "unknown")).inc()
    return result


@router.post("/cryptobot", status_code=status.HTTP_200_OK)
async def cryptobot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle webhook callbacks from CryptoBot payment service."""
    body = await request.body()
    signature = request.headers.get("crypto-pay-api-signature", "")
    cryptobot_token = settings.cryptobot_token.get_secret_value()

    signature_decision = verify_stage1_webhook_signature(
        Stage1PaymentProvider.CRYPTOBOT,
        body=body,
        headers=request.headers,
        secret=cryptobot_token,
    )
    if not signature_decision.accepted:
        webhook_operations_total.labels(provider="cryptobot", status=signature_decision.status.value).inc()
        raise InvalidWebhookSignatureError()

    handler = CryptoBotWebhookHandler(cryptobot_token)
    use_case = ProcessPaymentWebhookUseCase(webhook_handler=handler, session=db)

    result = await use_case.execute(provider="cryptobot", body=body, signature=signature)
    webhook_operations_total.labels(provider="cryptobot", status=result.get("status", "unknown")).inc()
    return result
