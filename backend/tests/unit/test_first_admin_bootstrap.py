"""Unit checks for the one-time first admin bootstrap CLI."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_bootstrap_module():
    module_path = Path(__file__).parents[2] / "scripts" / "bootstrap_first_admin.py"
    spec = importlib.util.spec_from_file_location("bootstrap_first_admin", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _valid_env() -> dict[str, str]:
    return {
        "CYBERVPN_BOOTSTRAP_CONFIRM": "CREATE_FIRST_ADMIN",
        "CYBERVPN_BOOTSTRAP_OWNER_HANDLE": "@Sasha_Beep",
        "CYBERVPN_BOOTSTRAP_LOGIN": "sasha.beep",
        "CYBERVPN_BOOTSTRAP_EMAIL": "owner@cyber-vpn.net",
        "CYBERVPN_BOOTSTRAP_PASSWORD": "correct-horse-battery-42!",
        "CYBERVPN_BOOTSTRAP_TOTP_SECRET": "JBSWY3DPEHPK3PXP",
        "CYBERVPN_BOOTSTRAP_TOTP_CODE": "123456",
    }


class TestFirstAdminBootstrapConfig:
    def test_script_prioritizes_backend_root_for_direct_cli_execution(self):
        _load_bootstrap_module()

        backend_root = str(Path(__file__).parents[2])
        assert sys.path[0] == backend_root

    def test_load_config_requires_explicit_confirmation(self):
        module = _load_bootstrap_module()
        env = _valid_env()
        env["CYBERVPN_BOOTSTRAP_CONFIRM"] = "YES"

        with pytest.raises(module.BootstrapError) as exc_info:
            module.load_config_from_env(env)

        assert exc_info.value.code == "confirmation_required"

    def test_load_config_rejects_weak_password(self):
        module = _load_bootstrap_module()
        env = _valid_env()
        env["CYBERVPN_BOOTSTRAP_PASSWORD"] = "admin-password-123456"

        with pytest.raises(module.BootstrapError) as exc_info:
            module.load_config_from_env(env)

        assert exc_info.value.code == "weak_password"

    def test_redacted_config_and_audit_payload_do_not_expose_secrets(self):
        module = _load_bootstrap_module()
        config = module.load_config_from_env(_valid_env())

        redacted = config.redacted()
        audit_payload = module.build_audit_payload(config)
        combined = f"{redacted} {audit_payload}"

        assert redacted["password_supplied"] is True
        assert redacted["totp_secret_supplied"] is True
        assert audit_payload["role"] == "owner/super_admin"
        assert audit_payload["default_credentials"] is False
        assert audit_payload["permanent_public_endpoint"] is False
        assert "correct-horse-battery-42!" not in combined
        assert "JBSWY3DPEHPK3PXP" not in combined
        assert "123456" not in combined
