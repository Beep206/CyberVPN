from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from src.config.settings import settings

MAX_SUBSCRIPTION_RESPONSE_BYTES = 8 * 1024 * 1024
FORWARDED_RESPONSE_HEADERS = frozenset(
    {
        "cache-control",
        "announce",
        "announce-url",
        "autorouting",
        "content-disposition",
        "content-type",
        "profile-title",
        "profile-update-interval",
        "profile-web-page-url",
        "routing",
        "subscription-userinfo",
        "support-url",
    }
)


class SubscriptionUpstreamNotFoundError(Exception):
    """Remnawave rejected or did not find the public subscription token."""


class SubscriptionUpstreamUnavailableError(Exception):
    """Remnawave did not return a safe bounded subscription response."""


@dataclass(frozen=True)
class SubscriptionProxyResponse:
    content: bytes
    headers: dict[str, str]


class RemnawaveSubscriptionProxyClient:
    """Unauthenticated internal client for Remnawave's public subscription route."""

    def __init__(self) -> None:
        self._base_url = self._validated_base_url(settings.remnawave_url)
        self._client: httpx.AsyncClient | None = None

    @staticmethod
    def _validated_base_url(raw_url: str) -> str:
        normalized = raw_url.rstrip("/").removesuffix("/api")
        parsed = urlparse(normalized)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("REMNAWAVE_URL is not a valid subscription upstream base URL")
        return normalized

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(30.0, connect=5.0, pool=5.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                follow_redirects=False,
                trust_env=False,
            )
        return self._client

    async def fetch(
        self,
        short_uuid: str,
        *,
        headers: dict[str, str],
    ) -> SubscriptionProxyResponse:
        client = await self._get_client()
        try:
            async with client.stream("GET", f"/api/sub/{short_uuid}", headers=headers) as response:
                if response.status_code in {403, 404, 410}:
                    raise SubscriptionUpstreamNotFoundError
                if response.status_code != 200:
                    raise SubscriptionUpstreamUnavailableError

                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        if int(content_length) > MAX_SUBSCRIPTION_RESPONSE_BYTES:
                            raise SubscriptionUpstreamUnavailableError
                    except ValueError as exc:
                        raise SubscriptionUpstreamUnavailableError from exc

                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_SUBSCRIPTION_RESPONSE_BYTES:
                        raise SubscriptionUpstreamUnavailableError

                safe_headers = {}
                for name, value in response.headers.items():
                    normalized_name = name.lower()
                    if (
                        normalized_name in FORWARDED_RESPONSE_HEADERS
                        or normalized_name.startswith("x-hwid-")
                        or normalized_name.startswith("x-cybervpn-")
                    ) and len(value) <= 4096:
                        safe_headers[normalized_name] = value
        except httpx.RequestError as exc:
            raise SubscriptionUpstreamUnavailableError from exc
        safe_headers["cache-control"] = "no-store"
        return SubscriptionProxyResponse(content=bytes(content), headers=safe_headers)

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


remnawave_subscription_proxy_client = RemnawaveSubscriptionProxyClient()
