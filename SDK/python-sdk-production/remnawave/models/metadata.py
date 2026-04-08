from typing import Any, Dict

from pydantic import BaseModel, Field


class MetadataDto(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GetUserMetadataResponseDto(MetadataDto):
    pass


class UpsertUserMetadataRequestDto(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpsertUserMetadataResponseDto(MetadataDto):
    pass


class GetNodeMetadataResponseDto(MetadataDto):
    pass


class UpsertNodeMetadataRequestDto(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpsertNodeMetadataResponseDto(MetadataDto):
    pass
