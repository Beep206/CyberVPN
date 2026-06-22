from __future__ import annotations

from fastapi import Response

from src.application.use_cases.partner_attribution.utils import PARTNER_ATTRIBUTION_COOKIE_NAME
from src.application.use_cases.referrals.attribution import REFERRAL_ATTRIBUTION_COOKIE_NAME
from src.presentation.api.v1.checkout_sessions import routes as checkout_session_routes
from src.presentation.api.v1.partner_attribution import routes as partner_attribution_routes
from src.presentation.api.v1.quotes import routes as quote_routes
from src.presentation.api.v1.referral import routes as referral_routes


def _latest_cookie_header(response: Response, cookie_name: str) -> str:
    headers = [header for header in response.headers.getlist("set-cookie") if header.startswith(f"{cookie_name}=")]
    assert headers
    return headers[-1].lower()


def test_partner_attribution_cookie_is_secure_in_staging_and_local_stage(monkeypatch) -> None:
    monkeypatch.setattr(partner_attribution_routes.settings, "cookie_secure", True)

    for environment in ("staging", "local-stage"):
        monkeypatch.setattr(partner_attribution_routes.settings, "environment", environment)
        response = Response()
        partner_attribution_routes._set_attribution_cookie(response, "cookie-token", max_age_seconds=3600)
        set_cookie = _latest_cookie_header(response, PARTNER_ATTRIBUTION_COOKIE_NAME)
        assert "secure" in set_cookie
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie
        assert "path=/" in set_cookie

        delete_response = Response()
        partner_attribution_routes._clear_attribution_cookie(delete_response)
        delete_cookie = _latest_cookie_header(delete_response, PARTNER_ATTRIBUTION_COOKIE_NAME)
        assert "max-age=0" in delete_cookie
        assert "secure" in delete_cookie
        assert "httponly" in delete_cookie
        assert "samesite=lax" in delete_cookie
        assert "path=/" in delete_cookie

        quote_delete_response = Response()
        quote_routes._clear_attribution_cookie(quote_delete_response)
        quote_delete_cookie = _latest_cookie_header(quote_delete_response, PARTNER_ATTRIBUTION_COOKIE_NAME)
        assert "max-age=0" in quote_delete_cookie
        assert "secure" in quote_delete_cookie
        assert "httponly" in quote_delete_cookie
        assert "samesite=lax" in quote_delete_cookie
        assert "path=/" in quote_delete_cookie

        checkout_delete_response = Response()
        checkout_session_routes._clear_attribution_cookie(checkout_delete_response)
        checkout_delete_cookie = _latest_cookie_header(
            checkout_delete_response,
            PARTNER_ATTRIBUTION_COOKIE_NAME,
        )
        assert "max-age=0" in checkout_delete_cookie
        assert "secure" in checkout_delete_cookie
        assert "httponly" in checkout_delete_cookie
        assert "samesite=lax" in checkout_delete_cookie
        assert "path=/" in checkout_delete_cookie


def test_attribution_cookies_allow_explicit_development_http_exception(monkeypatch) -> None:
    monkeypatch.setattr(partner_attribution_routes.settings, "environment", "development")
    monkeypatch.setattr(partner_attribution_routes.settings, "cookie_secure", False)
    monkeypatch.setattr(referral_routes.settings, "environment", "development")
    monkeypatch.setattr(referral_routes.settings, "cookie_secure", False)

    partner_response = Response()
    partner_attribution_routes._set_attribution_cookie(partner_response, "cookie-token", max_age_seconds=3600)
    assert "secure" not in _latest_cookie_header(partner_response, PARTNER_ATTRIBUTION_COOKIE_NAME)

    referral_response = Response()
    referral_routes._set_attribution_cookie(referral_response, "referral-cookie-token")
    assert "secure" not in _latest_cookie_header(referral_response, REFERRAL_ATTRIBUTION_COOKIE_NAME)
