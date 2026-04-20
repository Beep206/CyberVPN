from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LegalDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_key: str
    document_type: str
    locale: str
    title: str
    content_markdown: str
    content_checksum: str
    policy_version_id: UUID
    created_at: datetime
    updated_at: datetime


class CreateLegalDocumentRequest(BaseModel):
    document_key: str = Field(..., min_length=1, max_length=80)
    document_type: str = Field(..., min_length=1, max_length=30)
    locale: str = Field(..., min_length=2, max_length=16)
    title: str = Field(..., min_length=1, max_length=200)
    content_markdown: str = Field(..., min_length=1)
    policy_version_id: UUID


class LegalDocumentSetItemRequest(BaseModel):
    legal_document_id: UUID
    required: bool = True
    display_order: int = Field(default=0, ge=0)


class LegalDocumentSetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_document_id: UUID
    required: bool
    display_order: int


class LegalDocumentSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    set_key: str
    storefront_id: UUID
    auth_realm_id: UUID | None
    display_name: str
    policy_version_id: UUID
    documents: list[LegalDocumentSetItemResponse]
    created_at: datetime
    updated_at: datetime


class CreateLegalDocumentSetRequest(BaseModel):
    set_key: str = Field(..., min_length=1, max_length=80)
    storefront_id: UUID
    auth_realm_id: UUID | None = None
    display_name: str = Field(..., min_length=1, max_length=120)
    policy_version_id: UUID
    documents: list[LegalDocumentSetItemRequest] = Field(..., min_length=1)
