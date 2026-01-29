from uuid import UUID

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient


class CreateCryptoInvoiceUseCase:
    def __init__(self, crypto_client: CryptoBotClient, plan_repo: SubscriptionPlanRepository) -> None:
        self._crypto = crypto_client
        self._plan_repo = plan_repo

    async def execute(self, user_uuid: UUID, plan_id: UUID, currency: str) -> InvoiceResponseDTO:
        plan = await self._plan_repo.get_by_id(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        amount = str(plan.price_usd)
        description = f"CyberVPN {plan.name} - {plan.duration_days} days"
        payload = f"{user_uuid}:{plan_id}"

        result = await self._crypto.create_invoice(
            amount=amount, currency=currency, description=description, payload=payload
        )

        from datetime import datetime
        return InvoiceResponseDTO(
            invoice_id=str(result.get("invoice_id", "")),
            payment_url=result.get("pay_url", result.get("bot_invoice_url", "")),
            amount=plan.price_usd,
            currency=currency,
            expires_at=datetime.fromisoformat(result["expiration_date"]) if result.get("expiration_date") else datetime.now(),
        )
