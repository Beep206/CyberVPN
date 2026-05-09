"""S1 OAuth provider scope guardrails.

DEC-S1-019 allows only Google and GitHub OAuth login in the controlled public
beta. Other provider implementations may remain in code for later stages, but
they must not become active through accidental runtime configuration.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.config.settings import Settings
from src.presentation.api.v1.oauth import routes
from src.presentation.api.v1.oauth.schemas import OAuthProvider

S1_ALLOWED_OAUTH_PROVIDERS = {"google", "github"}
NON_S1_OAUTH_PROVIDERS = {"apple", "discord", "facebook", "microsoft", "twitter"}


def test_settings_default_oauth_provider_scope_is_s1_only():
    """Default runtime config exposes only the S1-approved OAuth providers."""
    assert set(Settings.model_fields["oauth_enabled_login_providers"].default) == S1_ALLOWED_OAUTH_PROVIDERS
    assert set(Settings.model_fields["oauth_trusted_email_link_providers"].default) == S1_ALLOWED_OAUTH_PROVIDERS


def test_route_gate_ignores_non_s1_provider_even_if_misconfigured(monkeypatch):
    """A broad env allowlist must not activate deferred OAuth providers in S1."""
    monkeypatch.setattr(
        routes.settings,
        "oauth_enabled_login_providers",
        ["google", "github", "discord", "facebook", "microsoft", "twitter", "apple"],
    )

    assert routes._is_oauth_login_provider_enabled("google") is True
    assert routes._is_oauth_login_provider_enabled("github") is True
    for provider in NON_S1_OAUTH_PROVIDERS:
        assert routes._is_oauth_login_provider_enabled(provider) is False


@pytest.mark.parametrize("provider", [OAuthProvider.GOOGLE, OAuthProvider.GITHUB])
def test_s1_providers_validate_for_login(provider, monkeypatch):
    monkeypatch.setattr(routes.settings, "oauth_enabled_login_providers", ["google", "github"])

    routes._validate_oauth_login_provider(provider)


@pytest.mark.parametrize(
    "provider",
    [
        OAuthProvider.APPLE,
        OAuthProvider.DISCORD,
        OAuthProvider.FACEBOOK,
        OAuthProvider.MICROSOFT,
        OAuthProvider.TWITTER,
    ],
)
def test_non_s1_providers_are_rejected_for_login(provider, monkeypatch):
    monkeypatch.setattr(
        routes.settings,
        "oauth_enabled_login_providers",
        ["google", "github", "discord", "facebook", "microsoft", "twitter", "apple"],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes._validate_oauth_login_provider(provider)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == f"Provider '{provider.value}' is currently disabled."


@pytest.mark.parametrize("provider", [OAuthProvider.GOOGLE, OAuthProvider.GITHUB])
def test_s1_login_providers_require_pkce(provider):
    """Both S1 OAuth providers use S256 PKCE in the backend authorize flow."""
    _, requires_pkce = routes._OAUTH_PROVIDERS[provider.value]

    assert requires_pkce is True


def test_web_callback_uri_uses_primary_s1_domain(monkeypatch):
    monkeypatch.setattr(routes.settings, "oauth_web_base_url", "https://cyber-vpn.net")
    monkeypatch.setattr(routes.settings, "oauth_allowed_redirect_uris", ["cybervpn://oauth/callback"])

    assert (
        routes._resolve_oauth_login_redirect_uri("google", None)
        == "https://cyber-vpn.net/api/oauth/callback/google"
    )
    assert (
        routes._resolve_oauth_login_redirect_uri("github", None)
        == "https://cyber-vpn.net/api/oauth/callback/github"
    )


def test_oauth_redirect_override_must_be_exact_native_uri(monkeypatch):
    monkeypatch.setattr(routes.settings, "oauth_web_base_url", "https://cyber-vpn.net")
    monkeypatch.setattr(routes.settings, "oauth_allowed_redirect_uris", ["cybervpn://oauth/callback"])

    assert routes._resolve_oauth_login_redirect_uri("github", "cybervpn://oauth/callback") == (
        "cybervpn://oauth/callback"
    )

    with pytest.raises(HTTPException) as exc_info:
        routes._resolve_oauth_login_redirect_uri("github", "https://cyber-vpn.org/oauth/callback")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid OAuth redirect URI."


@pytest.mark.parametrize("provider", ["facebook", "discord", "microsoft", "twitter", "apple"])
def test_code_oauth_linking_gate_blocks_non_s1_providers(provider, monkeypatch):
    monkeypatch.setattr(
        routes.settings,
        "oauth_enabled_login_providers",
        ["google", "github", "discord", "facebook", "microsoft", "twitter", "apple"],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes._validate_code_oauth_link_provider(provider)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == f"Provider '{provider}' is currently disabled."
