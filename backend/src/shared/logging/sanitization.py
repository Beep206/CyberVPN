"""URL and header sanitization for logging (LOW-004).

Removes sensitive information from URLs and headers before logging.
"""

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Sensitive query parameter names to redact
SENSITIVE_PARAMS = frozenset({
    "password", "pwd", "pass", "secret", "token", "api_key", "apikey",
    "api-key", "access_token", "refresh_token", "bearer", "auth",
    "authorization", "key", "code", "otp", "pin", "ssn", "credit_card",
    "card_number", "cvv", "expiry", "session", "session_id", "sessionid",
})

# Sensitive header names to redact
SENSITIVE_HEADERS = frozenset({
    "authorization", "x-api-key", "x-auth-token", "cookie", "set-cookie",
    "x-csrf-token", "x-xsrf-token", "api-key", "bearer",
})

REDACTED = "[REDACTED]"


def sanitize_url(url: str, *, redact_value: str = REDACTED) -> str:
    """Remove sensitive query parameters from URL.

    Args:
        url: The URL to sanitize.
        redact_value: Value to replace sensitive parameters with.

    Returns:
        Sanitized URL with sensitive parameters redacted.

    Example:
        >>> sanitize_url("https://api.com/auth?token=secret123&user=john")
        "https://api.com/auth?token=[REDACTED]&user=john"
    """
    try:
        parsed = urlparse(url)

        if not parsed.query:
            return url

        params = parse_qs(parsed.query, keep_blank_values=True)
        sanitized_params = {}

        for key, values in params.items():
            if key.lower() in SENSITIVE_PARAMS:
                sanitized_params[key] = [redact_value]
            else:
                sanitized_params[key] = values

        # Reconstruct URL with sanitized query string
        sanitized_query = urlencode(sanitized_params, doseq=True)
        sanitized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            sanitized_query,
            parsed.fragment,
        ))

        return sanitized

    except Exception:
        # If parsing fails, return original URL
        return url


def sanitize_headers(
    headers: dict[str, str],
    *,
    redact_value: str = REDACTED,
) -> dict[str, str]:
    """Remove sensitive values from headers dict.

    Args:
        headers: Dictionary of header name -> value.
        redact_value: Value to replace sensitive headers with.

    Returns:
        New dict with sensitive values redacted.

    Example:
        >>> sanitize_headers({"Authorization": "Bearer secret", "Content-Type": "json"})
        {"Authorization": "[REDACTED]", "Content-Type": "json"}
    """
    sanitized = {}

    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = redact_value
        elif key.lower() == "authorization" and value.lower().startswith("bearer "):
            # Special handling for bearer tokens
            sanitized[key] = f"Bearer {redact_value}"
        else:
            sanitized[key] = value

    return sanitized


def sanitize_path_params(path: str, *, patterns: list[str] | None = None) -> str:
    """Sanitize sensitive path parameters like UUIDs after certain endpoints.

    Args:
        path: The URL path to sanitize.
        patterns: List of regex patterns to redact (default includes UUID).

    Returns:
        Path with sensitive parameters redacted.
    """
    if patterns is None:
        # Default: redact UUIDs (common for user IDs, tokens)
        patterns = [
            r"/users/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            r"/tokens/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        ]

    sanitized = path
    for pattern in patterns:
        sanitized = re.sub(
            pattern,
            lambda m: m.group(0).rsplit("/", 1)[0] + "/" + REDACTED,
            sanitized,
            flags=re.IGNORECASE,
        )

    return sanitized
