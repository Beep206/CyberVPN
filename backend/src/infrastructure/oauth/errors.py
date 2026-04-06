"""OAuth provider infrastructure errors."""


class OAuthProviderUnavailableError(Exception):
    """Raised when the upstream OAuth provider is temporarily unreachable."""
