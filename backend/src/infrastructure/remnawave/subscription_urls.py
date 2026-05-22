"""Public subscription URL normalization for Remnawave-issued links."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from src.config.settings import settings

_KNOWN_SUBSCRIPTION_HOSTS = {
    "api.cyber-vpn.net",
    "cyber-vpn.net",
}
_SUBSCRIPTION_PATH_PREFIX = "/api/sub"


def normalize_public_subscription_url(url: str | None) -> str | None:
    """Rewrite CyberVPN subscription URLs to the approved public .org surface."""

    if not url:
        return url

    public_base = settings.remnawave_subscription_public_base_url.strip().rstrip("/")
    if not public_base:
        return url

    try:
        parsed = urlsplit(url)
        public = urlsplit(public_base)
    except ValueError:
        return url

    if parsed.scheme not in {"http", "https"}:
        return url
    if parsed.hostname not in _KNOWN_SUBSCRIPTION_HOSTS:
        return url
    if not parsed.path.startswith(_SUBSCRIPTION_PATH_PREFIX):
        return url
    if not public.scheme or not public.netloc:
        return url

    suffix = parsed.path[len(_SUBSCRIPTION_PATH_PREFIX):]
    public_path = f"{public.path.rstrip('/')}{suffix}"
    return urlunsplit((public.scheme, public.netloc, public_path, parsed.query, parsed.fragment))


def normalize_public_subscription_urls(urls: list[str]) -> list[str]:
    """Normalize a list of subscription URLs while preserving non-subscription links."""

    return [normalize_public_subscription_url(url) or url for url in urls]
