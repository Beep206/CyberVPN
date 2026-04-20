from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AcceptedLegalDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_document_id: UUID | None
    legal_document_set_id: UUID | None
    storefront_id: UUID
    auth_realm_id: UUID
    actor_principal_id: UUID
    actor_principal_type: str
    acceptance_channel: str
    quote_session_id: UUID | None
    checkout_session_id: UUID | None
    order_id: UUID | None
    source_ip: str | None
    user_agent: str | None
    device_context: dict | None
    accepted_at: datetime


class CreateAcceptedLegalDocumentRequest(BaseModel):
    legal_document_id: UUID | None = None
    legal_document_set_id: UUID | None = None
    storefront_id: UUID
    acceptance_channel: str = Field(..., min_length=1, max_length=50)
    quote_session_id: UUID | None = None
    checkout_session_id: UUID | None = None
    order_id: UUID | None = None
    device_context: dict | None = None


class ListAcceptedLegalDocumentsFilters(BaseModel):
    actor_principal_id: UUID | None = None
    storefront_id: UUID | None = None
    auth_realm_id: UUID | None = None
    order_id: UUID | None = None
    acceptance_channel: str | None = Field(default=None, max_length=50)
