"""OAuth provider token retention policy.

Login-only providers should not persist third-party access/refresh tokens by
default. Retention must be explicitly allowlisted per provider and token type.
"""

from dataclasses import dataclass

from src.config.settings import settings


@dataclass(frozen=True)
class StoredOAuthTokens:
    """Normalized token payload that may be persisted for a linked provider."""

    access_token: str | None
    refresh_token: str | None


def build_stored_oauth_tokens(
    provider: str,
    access_token: str | None,
    refresh_token: str | None,
) -> StoredOAuthTokens:
    """Return the minimum token set that may be persisted for a provider."""
    normalized_provider = provider.strip().lower()

    stored_access_token = (
        access_token
        if normalized_provider in settings.oauth_retained_access_token_providers and access_token
        else None
    )
    stored_refresh_token = (
        refresh_token
        if normalized_provider in settings.oauth_retained_refresh_token_providers and refresh_token
        else None
    )

    return StoredOAuthTokens(
        access_token=stored_access_token,
        refresh_token=stored_refresh_token,
    )
