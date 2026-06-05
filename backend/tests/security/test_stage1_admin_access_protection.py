"""S1-ADM-001 admin host/access protection checks."""

from __future__ import annotations

from src.presentation.middleware.admin_host_guard import is_admin_host_protected_path, normalize_host


def test_stage1_admin_host_guard_normalizes_hosts() -> None:
    assert normalize_host("ADMIN.CYBER-VPN.NET:443") == "admin.cyber-vpn.net"
    assert normalize_host("https://admin.cyber-vpn.net") == "admin.cyber-vpn.net"
    assert normalize_host("[::1]:8000") == "::1"
    assert normalize_host("admin.cyber-vpn.net, evil.example") == "admin.cyber-vpn.net"


def test_stage1_admin_host_guard_path_scope() -> None:
    assert is_admin_host_protected_path("/api/v1/admin")
    assert is_admin_host_protected_path("/api/v1/admin/audit-log")
    assert not is_admin_host_protected_path("/api/v1/adminish")
    assert not is_admin_host_protected_path("/api/v1/admin/growth-reporting/internal/refresh")
    assert not is_admin_host_protected_path("/api/v1/status")


def test_stage1_production_admin_api_requires_admin_host(
    production_app_security_snapshot: dict,
) -> None:
    assert production_app_security_snapshot["admin_host"] == {
        "allowed_host": {
            "body": {"detail": "Not authenticated"},
            "status": 401,
        },
        "allowed_preflight": {
            "allow_origin": "https://admin.cyber-vpn.net",
            "status": 200,
        },
        "redirect_only_host": {
            "body": {"detail": "Not found"},
            "status": 404,
        },
        "status": {
            "status": 200,
        },
        "wrong_host": {
            "body": {"detail": "Not found"},
            "status": 404,
        },
        "wrong_preflight": {
            "allow_origin": None,
            "status": 404,
        },
    }
