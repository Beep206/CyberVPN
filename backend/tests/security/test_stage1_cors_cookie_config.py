"""S1-BE-005 CORS and cookie-domain production safety checks."""

from __future__ import annotations


def test_stage1_production_app_cors_allows_only_primary_net_origins(
    production_app_security_snapshot: dict,
) -> None:
    assert production_app_security_snapshot["cors_cookie"] == {
        "admin_preflight": {
            "allow_credentials": "true",
            "allow_origin": "https://admin.cyber-vpn.net",
            "status": 200,
        },
        "cookie_domain": "cyber-vpn.net",
        "cookie_secure": True,
        "cors_origins": [
            "https://cyber-vpn.net",
            "https://admin.cyber-vpn.net",
        ],
        "public_preflight": {
            "allow_credentials": "true",
            "allow_origin": "https://cyber-vpn.net",
            "status": 200,
        },
        "redirect_only_preflight": {
            "allow_origin": None,
            "status": 400,
        },
    }
