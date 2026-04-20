"""Brand, storefront, and profile domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Brand:
    id: UUID
    brand_key: str
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MerchantProfile:
    id: UUID
    profile_key: str
    legal_entity_name: str
    billing_descriptor: str
    supported_currencies: list[str]
    tax_behavior: dict[str, Any]
    refund_responsibility_model: str
    chargeback_liability_model: str
    status: str
    created_at: datetime
    updated_at: datetime
    invoice_profile_id: UUID | None = None
    settlement_reference: str | None = None


@dataclass(frozen=True)
class InvoiceProfile:
    id: UUID
    profile_key: str
    display_name: str
    issuer_legal_name: str
    tax_identifier: str | None
    issuer_email: str | None
    tax_behavior: dict[str, Any]
    invoice_footer: str | None
    receipt_footer: str | None
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class BillingDescriptor:
    id: UUID
    descriptor_key: str
    merchant_profile_id: UUID
    statement_descriptor: str
    soft_descriptor: str | None
    support_phone: str | None
    support_url: str | None
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime
    invoice_profile_id: UUID | None = None


@dataclass(frozen=True)
class SupportProfile:
    id: UUID
    profile_key: str
    support_email: str
    help_center_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CommunicationProfile:
    id: UUID
    profile_key: str
    sender_domain: str
    from_email: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Storefront:
    id: UUID
    storefront_key: str
    brand_id: UUID
    display_name: str
    host: str
    status: str
    created_at: datetime
    updated_at: datetime
    auth_realm_id: UUID | None = None
    merchant_profile_id: UUID | None = None
    support_profile_id: UUID | None = None
    communication_profile_id: UUID | None = None
