from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RealmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    realm_key: str
    realm_type: str
    display_name: str
    audience: str
    cookie_namespace: str
    status: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class RealmResolutionResponse(BaseModel):
    realm: RealmResponse
    source: str
    host: str | None = None
