"""Telegram OIDC ID token validation service for mobile native login."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from jwt.algorithms import RSAAlgorithm

from src.config.settings import settings
from src.infrastructure.oauth.oidc import AsyncOIDCTokenVerifier

logger = logging.getLogger(__name__)


class InvalidTelegramOIDCTokenError(Exception):
    """Raised when a Telegram OIDC ID token is invalid."""

    def __init__(
        self,
        message: str = "Invalid Telegram ID token",
        *,
        reason: str = "invalid_token",
    ) -> None:
        self.message = message
        self.reason = reason
        super().__init__(self.message)


@dataclass(frozen=True)
class TelegramOIDCUserInfo:
    """Validated Telegram OIDC claims relevant to the backend."""

    subject: str
    telegram_id: int | None
    name: str | None
    preferred_username: str | None
    picture: str | None
    phone_number: str | None
    issued_at: datetime
    expires_at: datetime


class TelegramOIDCAuthService:
    """Validate Telegram OIDC ID tokens returned by the native SDK."""

    SUPPORTED_ALGORITHM = "RS256"

    def __init__(self) -> None:
        self._client_id = settings.telegram_oidc_client_id.strip()
        self._allowed_audience = (settings.telegram_oidc_allowed_audience or self._client_id).strip()
        self._issuer = settings.telegram_oidc_issuer.strip()
        self._discovery_url = settings.telegram_oidc_discovery_url.strip()
        self._jwks_url = settings.telegram_oidc_jwks_url.strip()
        self._clock_skew_seconds = settings.telegram_oidc_clock_skew_seconds

    async def validate_id_token(self, id_token: str) -> TelegramOIDCUserInfo:
        """Validate a Telegram OIDC ID token and normalize its claims."""
        if not self._client_id or not self._allowed_audience:
            raise InvalidTelegramOIDCTokenError(
                "Telegram OIDC client ID is not configured",
                reason="not_configured",
            )

        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token header is malformed",
                reason="header_invalid",
            ) from exc

        kid = header.get("kid")
        algorithm = header.get("alg")
        if not kid:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token is missing kid",
                reason="kid_missing",
            )
        if algorithm != self.SUPPORTED_ALGORITHM:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token uses an unsupported algorithm",
                reason="alg_invalid",
            )

        discovery = await AsyncOIDCTokenVerifier._fetch_json_cached(
            self._discovery_url,
            cache=AsyncOIDCTokenVerifier._metadata_cache,
            cache_label="telegram_oidc_metadata",
        )
        discovery_issuer = discovery.get("issuer")
        if discovery_issuer != self._issuer:
            raise InvalidTelegramOIDCTokenError(
                "Telegram OIDC discovery issuer does not match configuration",
                reason="discovery_issuer_invalid",
            )

        jwks_uri = discovery.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri:
            raise InvalidTelegramOIDCTokenError(
                "Telegram OIDC discovery document is missing jwks_uri",
                reason="jwks_uri_missing",
            )
        if self._jwks_url and jwks_uri != self._jwks_url:
            raise InvalidTelegramOIDCTokenError(
                "Telegram OIDC discovery JWKS URI does not match configuration",
                reason="jwks_uri_invalid",
            )

        jwks = await AsyncOIDCTokenVerifier._fetch_json_cached(
            jwks_uri,
            cache=AsyncOIDCTokenVerifier._jwks_cache,
            cache_label="telegram_oidc_jwks",
        )
        key_data = next((item for item in jwks.get("keys", []) if item.get("kid") == kid), None)
        if not key_data:
            jwks = await AsyncOIDCTokenVerifier._fetch_json_cached(
                jwks_uri,
                cache=AsyncOIDCTokenVerifier._jwks_cache,
                cache_label="telegram_oidc_jwks",
                force_refresh=True,
            )
            key_data = next((item for item in jwks.get("keys", []) if item.get("kid") == kid), None)
            if not key_data:
                raise InvalidTelegramOIDCTokenError(
                    "Telegram ID token signing key was not found",
                    reason="kid_unknown",
                )

        signing_key = RSAAlgorithm.from_jwk(json.dumps(key_data))

        try:
            claims = jwt.decode(
                id_token,
                key=signing_key,
                algorithms=[self.SUPPORTED_ALGORITHM],
                audience=self._allowed_audience,
                issuer=self._issuer,
                leeway=self._clock_skew_seconds,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token has expired",
                reason="expired",
            ) from exc
        except jwt.InvalidAudienceError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token audience is invalid",
                reason="aud_invalid",
            ) from exc
        except jwt.InvalidIssuerError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token issuer is invalid",
                reason="iss_invalid",
            ) from exc
        except jwt.ImmatureSignatureError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token iat is in the future",
                reason="iat_invalid",
            ) from exc
        except jwt.InvalidIssuedAtError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token iat is invalid",
                reason="iat_invalid",
            ) from exc
        except jwt.MissingRequiredClaimError as exc:
            raise InvalidTelegramOIDCTokenError(
                f"Telegram ID token is missing required claim: {exc.claim}",
                reason=f"missing_{exc.claim}",
            ) from exc
        except jwt.InvalidSignatureError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token signature is invalid",
                reason="signature_invalid",
            ) from exc
        except jwt.PyJWTError as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token is invalid",
                reason="token_invalid",
            ) from exc

        subject = str(claims.get("sub", "")).strip()
        if not subject:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token is missing subject",
                reason="sub_missing",
            )

        telegram_id = self._parse_optional_telegram_id(claims.get("id"))

        issued_at = datetime.fromtimestamp(int(claims["iat"]), tz=UTC)
        expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=UTC)

        return TelegramOIDCUserInfo(
            subject=subject,
            telegram_id=telegram_id,
            name=self._normalize_optional_str(claims.get("name")),
            preferred_username=self._normalize_optional_str(claims.get("preferred_username")),
            picture=self._normalize_optional_str(claims.get("picture")),
            phone_number=self._normalize_optional_str(claims.get("phone_number")),
            issued_at=issued_at,
            expires_at=expires_at,
        )

    @staticmethod
    def _normalize_optional_str(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _parse_optional_telegram_id(value: object) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise InvalidTelegramOIDCTokenError(
                "Telegram ID token contains an invalid numeric Telegram ID",
                reason="telegram_id_invalid",
            ) from exc
