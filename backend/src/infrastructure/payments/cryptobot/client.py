from httpx import AsyncClient

from src.config.settings import settings


class CryptoBotClient:
    BASE_URL = "https://pay.crypt.bot/api"

    def __init__(self) -> None:
        self._token = getattr(settings, "cryptobot_token", None)
        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(
                base_url=self.BASE_URL,
                headers={"Crypto-Pay-API-Token": self._token.get_secret_value() if self._token else ""},
                timeout=30.0,
            )
        return self._client

    async def create_invoice(
        self, amount: str, currency: str, description: str, payload: str | None = None
    ) -> dict:
        client = await self._get_client()
        params = {"amount": amount, "asset": currency, "description": description}
        if payload:
            params["payload"] = payload
        response = await client.post("/createInvoice", json=params)
        response.raise_for_status()
        data = response.json()
        return data.get("result", data)

    async def get_invoice(self, invoice_id: str) -> dict:
        client = await self._get_client()
        response = await client.get("/getInvoices", params={"invoice_ids": invoice_id})
        response.raise_for_status()
        data = response.json()
        items = data.get("result", {}).get("items", [])
        return items[0] if items else {}

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
