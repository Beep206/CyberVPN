from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CreateInvoiceDTO:
    user_uuid: UUID
    plan_id: UUID
    currency: str


@dataclass(frozen=True)
class InvoiceResponseDTO:
    invoice_id: str
    payment_url: str
    amount: Decimal
    currency: str
    expires_at: datetime
