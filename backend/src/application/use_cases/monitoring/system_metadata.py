"""Remnawave system metadata use case."""

from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveMetadataResponse


class SystemMetadataUseCase:
    """Fetch Remnawave panel metadata useful for operations."""

    def __init__(self, client: RemnawaveClient):
        self.client = client

    async def execute(self) -> dict:
        metadata = await self.client.get_validated("/api/system/metadata", RemnawaveMetadataResponse)
        return {
            "version": metadata.version,
            "build": metadata.build.model_dump(mode="json"),
            "git": metadata.git.model_dump(mode="json"),
        }
