from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.application.dto.payment_dto import InvoiceResponseDTO
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient


class CreateCryptoInvoiceUseCase:
    def __init__(self, crypto_client: CryptoBotClient, plan_repo: SubscriptionPlanRepository) -> None:
        self._crypto = crypto_client
        self._plan_repo = plan_repo

    async def execute(self, user_uuid: UUID, plan_id: str | UUID, currency: str) -> InvoiceResponseDTO:
        plan = await self._resolve_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        amount = Decimal(str(plan.price_usd))
        description = f"CyberVPN {plan.name} - {plan.duration_days} days"
        payload = f"{user_uuid}:{plan_id}"

        result = await self._crypto.create_invoice(
            amount=str(amount), currency=currency, description=description, payload=payload
        )

        return InvoiceResponseDTO(
            invoice_id=str(result.get("invoice_id", "")),
            payment_url=result.get("pay_url", result.get("bot_invoice_url", "")),
            amount=amount,
            currency=currency,
            status=result.get("status", "pending"),
            expires_at=self._parse_expiration(result.get("expiration_date")),
        )

    async def get_invoice(self, invoice_id: str) -> InvoiceResponseDTO | None:
        result = await self._crypto.get_invoice(invoice_id)
        if not result:
            return None

        amount = Decimal(str(result.get("amount", "0")))
        currency = result.get("asset") or result.get("currency") or ""
        status = result.get("status", "pending")

        return InvoiceResponseDTO(
            invoice_id=str(result.get("invoice_id", invoice_id)),
            payment_url=result.get("pay_url", result.get("bot_invoice_url", "")),
            amount=amount,
            currency=currency,
            status=status,
            expires_at=self._parse_expiration(result.get("expiration_date")),
        )

    async def _resolve_plan(self, plan_id: str | UUID):
        if isinstance(plan_id, UUID):
            return await self._plan_repo.get_by_id(plan_id)

        try:
            plan_uuid = UUID(str(plan_id))
        except ValueError:
            return await self._plan_repo.get_by_name(str(plan_id))

        return await self._plan_repo.get_by_id(plan_uuid)

    def _parse_expiration(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)

        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now(UTC)
