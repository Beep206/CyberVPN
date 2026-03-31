"""Async OIDC ID token verification helpers for social providers."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, ClassVar

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

logger = logging.getLogger(__name__)


class AsyncOIDCTokenVerifier:
    """Verify ID tokens against an OIDC discovery document and JWKS."""

    _metadata_cache: ClassVar[dict[str, tuple[float, dict[str, Any]]]] = {}
    _jwks_cache: ClassVar[dict[str, tuple[float, dict[str, Any]]]] = {}
    _default_cache_ttl_seconds = 3600

    @classmethod
    def _extract_cache_ttl(cls, cache_control: str | None) -> int:
        if not cache_control:
            return cls._default_cache_ttl_seconds

        for part in cache_control.split(","):
            name, _, value = part.strip().partition("=")
            if name.lower() == "max-age" and value.isdigit():
                return max(int(value), 60)

        return cls._default_cache_ttl_seconds

    @classmethod
    async def _fetch_json_cached(
        cls,
        url: str,
        *,
        cache: dict[str, tuple[float, dict[str, Any]]],
    ) -> dict[str, Any]:
        cached = cache.get(url)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            ttl_seconds = cls._extract_cache_ttl(response.headers.get("Cache-Control"))

        cache[url] = (now + ttl_seconds, payload)
        return payload

    @classmethod
    async def verify_id_token(
        cls,
        *,
        id_token: str,
        audience: str,
        discovery_url: str,
        issuer_validator,
        nonce: str | None = None,
    ) -> dict[str, Any] | None:
        """Verify an ID token using the provider's JWKS."""
        try:
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")
            algorithm = unverified_header.get("alg")
            if not kid or algorithm not in {"RS256", "RS384", "RS512"}:
                logger.warning("OIDC ID token missing supported kid/alg", extra={"alg": algorithm, "kid": kid})
                return None

            discovery = await cls._fetch_json_cached(discovery_url, cache=cls._metadata_cache)
            jwks_uri = discovery.get("jwks_uri")
            if not isinstance(jwks_uri, str) or not jwks_uri:
                logger.warning("OIDC discovery document missing jwks_uri", extra={"discovery_url": discovery_url})
                return None

            jwks = await cls._fetch_json_cached(jwks_uri, cache=cls._jwks_cache)
            key_data = next((item for item in jwks.get("keys", []) if item.get("kid") == kid), None)
            if not key_data:
                logger.warning("OIDC signing key not found for token kid", extra={"kid": kid, "jwks_uri": jwks_uri})
                return None

            signing_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
            claims = jwt.decode(
                id_token,
                key=signing_key,
                algorithms=[algorithm],
                audience=audience,
                options={"verify_iss": False},
            )

            if nonce is not None and claims.get("nonce") != nonce:
                logger.warning("OIDC nonce validation failed")
                return None

            if not issuer_validator(claims, discovery):
                logger.warning(
                    "OIDC issuer validation failed",
                    extra={"iss": claims.get("iss"), "discovery_url": discovery_url},
                )
                return None

            return claims

        except (httpx.HTTPError, jwt.PyJWTError, TypeError, ValueError) as exc:
            logger.warning("OIDC ID token verification failed", extra={"error": str(exc)})
            return None
