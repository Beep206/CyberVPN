from src.infrastructure.remnawave.client import RemnawaveClient, remnawave_client


async def get_remnawave_client() -> RemnawaveClient:
    return remnawave_client
