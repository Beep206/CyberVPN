from typing import Annotated

from rapid_api_client import Path
from rapid_api_client.annotations import PydanticBody

from remnawave.models import (
    GetNodeMetadataResponseDto,
    GetUserMetadataResponseDto,
    UpsertNodeMetadataRequestDto,
    UpsertNodeMetadataResponseDto,
    UpsertUserMetadataRequestDto,
    UpsertUserMetadataResponseDto,
)
from remnawave.rapid import BaseController, get, put


class MetadataController(BaseController):
    @get("/metadata/user/{uuid}", response_class=GetUserMetadataResponseDto)
    async def get_user_metadata(
        self,
        uuid: Annotated[str, Path(description="UUID of the user")],
    ) -> GetUserMetadataResponseDto:
        """Get User Metadata"""
        ...

    @put("/metadata/user/{uuid}", response_class=UpsertUserMetadataResponseDto)
    async def upsert_user_metadata(
        self,
        uuid: Annotated[str, Path(description="UUID of the user")],
        body: Annotated[UpsertUserMetadataRequestDto, PydanticBody()],
    ) -> UpsertUserMetadataResponseDto:
        """Update or Create User Metadata"""
        ...

    @get("/metadata/node/{uuid}", response_class=GetNodeMetadataResponseDto)
    async def get_node_metadata(
        self,
        uuid: Annotated[str, Path(description="UUID of the node")],
    ) -> GetNodeMetadataResponseDto:
        """Get Node Metadata"""
        ...

    @put("/metadata/node/{uuid}", response_class=UpsertNodeMetadataResponseDto)
    async def upsert_node_metadata(
        self,
        uuid: Annotated[str, Path(description="UUID of the node")],
        body: Annotated[UpsertNodeMetadataRequestDto, PydanticBody()],
    ) -> UpsertNodeMetadataResponseDto:
        """Update or Create Node Metadata"""
        ...
