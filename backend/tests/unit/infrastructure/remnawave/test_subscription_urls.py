from src.config.settings import settings
from src.infrastructure.remnawave.subscription_urls import (
    normalize_public_subscription_url,
    normalize_public_subscription_urls,
)


def test_normalize_public_subscription_url_rewrites_known_net_host(monkeypatch):
    monkeypatch.setattr(
        settings,
        "remnawave_subscription_public_base_url",
        "https://cyber-vpn.org/api/sub",
    )

    result = normalize_public_subscription_url("https://api.cyber-vpn.net/api/sub/6ho28HMU1j8b8M5V")

    assert result == "https://cyber-vpn.org/api/sub/6ho28HMU1j8b8M5V"


def test_normalize_public_subscription_url_preserves_query_and_fragment(monkeypatch):
    monkeypatch.setattr(
        settings,
        "remnawave_subscription_public_base_url",
        "https://cyber-vpn.org/api/sub",
    )

    result = normalize_public_subscription_url("https://cyber-vpn.net/api/sub/short?client=xray#profile")

    assert result == "https://cyber-vpn.org/api/sub/short?client=xray#profile"


def test_normalize_public_subscription_url_preserves_vless_config_link(monkeypatch):
    monkeypatch.setattr(
        settings,
        "remnawave_subscription_public_base_url",
        "https://cyber-vpn.org/api/sub",
    )

    result = normalize_public_subscription_url("vless://uuid@example.com:443?type=xhttp#DE-XHTTP")

    assert result == "vless://uuid@example.com:443?type=xhttp#DE-XHTTP"


def test_normalize_public_subscription_urls_preserves_non_subscription_links(monkeypatch):
    monkeypatch.setattr(
        settings,
        "remnawave_subscription_public_base_url",
        "https://cyber-vpn.org/api/sub",
    )

    result = normalize_public_subscription_urls(
        [
            "https://api.cyber-vpn.net/api/sub/short",
            "vless://uuid@example.com:443?type=tcp#DE-RAW",
        ]
    )

    assert result == [
        "https://cyber-vpn.org/api/sub/short",
        "vless://uuid@example.com:443?type=tcp#DE-RAW",
    ]
