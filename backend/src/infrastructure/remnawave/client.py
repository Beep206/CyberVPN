from httpx import AsyncClient

from src.config.settings import settings


class RemnawaveClient:
    def __init__(self) -> None:
        self._base_url = settings.remnawave_url.rstrip("/")
        self._token = settings.remnawave_token.get_secret_value()
        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30.0,
            )
        return self._client

    async def get(self, path: str, **kwargs) -> dict:
        client = await self._get_client()
        response = await client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, **kwargs) -> dict:
        client = await self._get_client()
        response = await client.post(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def put(self, path: str, **kwargs) -> dict:
        client = await self._get_client()
        response = await client.put(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def delete(self, path: str, **kwargs) -> dict:
        client = await self._get_client()
        response = await client.delete(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            await self.get("/api/health")
            return True
        except Exception:
            return False


remnawave_client = RemnawaveClient()


async def get_remnawave_client() -> RemnawaveClient:
    return remnawave_client
