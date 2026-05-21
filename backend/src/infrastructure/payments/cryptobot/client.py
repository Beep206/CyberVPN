from httpx import AsyncClient
from pydantic import SecretStr

from src.config.settings import settings


class CryptoBotClient:
    NETWORK_BASE_URLS = {
        "mainnet": "https://pay.crypt.bot/api",
        "testnet": "https://testnet-pay.crypt.bot/api",
    }
    SUPPORTED_CRYPTO_ASSETS = frozenset({"USDT", "TON", "BTC", "ETH", "LTC", "BNB", "TRX", "USDC"})
    SUPPORTED_FIAT_CURRENCIES = frozenset(
        {
            "USD",
            "EUR",
            "RUB",
            "BYN",
            "UAH",
            "GBP",
            "CNY",
            "KZT",
            "UZS",
            "GEL",
            "TRY",
            "AMD",
            "THB",
            "INR",
            "BRL",
            "IDR",
            "AZN",
            "AED",
            "PLN",
            "ILS",
        }
    )

    def __init__(self, token: SecretStr | None = None, network: str | None = None) -> None:
        self._token = token or getattr(settings, "cryptobot_token", None)
        self.network = network or getattr(settings, "cryptobot_network", "mainnet")
        if self.network not in self.NETWORK_BASE_URLS:
            raise ValueError("Unsupported CryptoBot network. Expected 'mainnet' or 'testnet'.")
        self.base_url = self.NETWORK_BASE_URLS[self.network]
        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(
                base_url=self.base_url,
                headers={"Crypto-Pay-API-Token": self._token.get_secret_value() if self._token else ""},
                timeout=30.0,
            )
        return self._client

    async def create_invoice(self, amount: str, currency: str, description: str, payload: str | None = None) -> dict:
        client = await self._get_client()
        params = self._build_create_invoice_payload(
            amount=amount,
            currency=currency,
            description=description,
            payload=payload,
        )
        response = await client.post("/createInvoice", json=params)
        response.raise_for_status()
        data = response.json()
        return data.get("result", data)

    def _build_create_invoice_payload(
        self,
        *,
        amount: str,
        currency: str,
        description: str,
        payload: str | None = None,
    ) -> dict:
        normalized_currency = currency.upper()
        params = {"amount": str(amount), "description": description}
        if normalized_currency in self.SUPPORTED_CRYPTO_ASSETS:
            params.update({"currency_type": "crypto", "asset": normalized_currency})
        elif normalized_currency in self.SUPPORTED_FIAT_CURRENCIES:
            params.update({"currency_type": "fiat", "fiat": normalized_currency})
        else:
            raise ValueError(f"Unsupported CryptoBot invoice currency: {currency}")
        if payload:
            params["payload"] = payload
        return params

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


cryptobot_client = CryptoBotClient(token=settings.cryptobot_token)


async def get_cryptobot_client() -> CryptoBotClient:
    return cryptobot_client
