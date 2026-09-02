from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import Settings


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "development",
        "jwt_secret": SecretStr("xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"),
        "remnawave_token": SecretStr("valid_token_for_testing_purposes_32characters"),
        "cryptobot_token": SecretStr("valid_token_for_testing_purposes_32characters"),
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.unit
def test_node_ssh_defaults_disabled_with_bounded_ticket_and_session_lifetimes() -> None:
    configured = _settings()

    assert configured.remnawave_node_ssh_enabled is False
    assert configured.remnawave_node_ssh_broker_url == ""
    assert configured.remnawave_node_ssh_broker_secret.get_secret_value() == ""
    assert configured.remnawave_node_ssh_trusted_admin_ids == ""
    assert configured.remnawave_node_ssh_allowed_node_ids == ""
    assert configured.remnawave_node_ssh_ticket_ttl_seconds == 15
    assert configured.remnawave_node_ssh_session_max_seconds == 1800
    assert configured.remnawave_node_ssh_revocation_poll_seconds == 0.5


@pytest.mark.unit
def test_enabling_node_ssh_requires_explicit_trusted_admin_and_node_allowlists() -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_NODE_SSH_TRUSTED_ADMIN_IDS"):
        _settings(
            remnawave_node_ssh_enabled=True,
            remnawave_node_ssh_broker_url="http://remnawave-ssh-proxy:8080",
            remnawave_node_ssh_broker_secret=SecretStr("a" * 128),
            passkey_enabled=True,
            passkey_admin_enabled=True,
        )

    with pytest.raises(ValidationError, match="REMNAWAVE_NODE_SSH_ALLOWED_NODE_IDS"):
        _settings(
            remnawave_node_ssh_enabled=True,
            remnawave_node_ssh_broker_url="http://remnawave-ssh-proxy:8080",
            remnawave_node_ssh_broker_secret=SecretStr("a" * 128),
            remnawave_node_ssh_trusted_admin_ids=str(uuid4()),
            passkey_enabled=True,
            passkey_admin_enabled=True,
        )


@pytest.mark.unit
def test_enabling_node_ssh_requires_admin_passkey_reauthentication() -> None:
    with pytest.raises(ValidationError, match="Admin passkey reauthentication"):
        _settings(
            remnawave_node_ssh_enabled=True,
            remnawave_node_ssh_broker_url="http://remnawave-ssh-proxy:8080",
            remnawave_node_ssh_broker_secret=SecretStr("a" * 128),
            remnawave_node_ssh_trusted_admin_ids=str(uuid4()),
            remnawave_node_ssh_allowed_node_ids=str(uuid4()),
        )


@pytest.mark.unit
def test_node_ssh_accepts_explicit_unique_admin_and_node_scope() -> None:
    admin_id = uuid4()
    node_id = uuid4()

    configured = _settings(
        remnawave_node_ssh_enabled=True,
        remnawave_node_ssh_broker_url="http://remnawave-ssh-proxy:8080",
        remnawave_node_ssh_broker_secret=SecretStr("a" * 128),
        remnawave_node_ssh_trusted_admin_ids=str(admin_id),
        remnawave_node_ssh_allowed_node_ids=str(node_id),
        passkey_enabled=True,
        passkey_admin_enabled=True,
    )

    assert configured.remnawave_node_ssh_enabled is True
    assert configured.remnawave_node_ssh_broker_url == "http://remnawave-ssh-proxy:8080"
    assert configured.remnawave_node_ssh_broker_secret.get_secret_value() == "a" * 128
    assert configured.remnawave_node_ssh_trusted_admin_ids == str(admin_id)
    assert configured.remnawave_node_ssh_allowed_node_ids == str(node_id)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("remnawave_node_ssh_ticket_ttl_seconds", 16),
        ("remnawave_node_ssh_session_max_seconds", 3601),
        ("remnawave_node_ssh_revocation_poll_seconds", 0.09),
    ],
)
def test_node_ssh_rejects_unbounded_lifetimes(field: str, value: int | float) -> None:
    with pytest.raises(ValidationError):
        _settings(**{field: value})


@pytest.mark.unit
@pytest.mark.parametrize("secret", ["", "a" * 127, "A" * 128, "g" * 128])
def test_node_ssh_requires_exact_dedicated_lowercase_hex_broker_secret(secret: str) -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_NODE_SSH_BROKER_SECRET"):
        _settings(
            remnawave_node_ssh_enabled=True,
            remnawave_node_ssh_broker_url="http://remnawave-ssh-proxy:8080",
            remnawave_node_ssh_broker_secret=SecretStr(secret),
            remnawave_node_ssh_trusted_admin_ids=str(uuid4()),
            remnawave_node_ssh_allowed_node_ids=str(uuid4()),
            passkey_enabled=True,
            passkey_admin_enabled=True,
        )


@pytest.mark.unit
def test_node_ssh_broker_secret_cannot_reuse_generic_remnawave_token() -> None:
    shared_secret = "a" * 128
    with pytest.raises(ValidationError, match="must differ from REMNAWAVE_TOKEN"):
        _settings(
            remnawave_token=SecretStr(shared_secret),
            remnawave_node_ssh_enabled=True,
            remnawave_node_ssh_broker_url="http://remnawave-ssh-proxy:8080",
            remnawave_node_ssh_broker_secret=SecretStr(shared_secret),
            remnawave_node_ssh_trusted_admin_ids=str(uuid4()),
            remnawave_node_ssh_allowed_node_ids=str(uuid4()),
            passkey_enabled=True,
            passkey_admin_enabled=True,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "broker_url",
    [
        "",
        "remnawave-ssh-proxy:8080",
        "http://user:password@remnawave-ssh-proxy:8080",
        "http://remnawave-ssh-proxy:8080/api",
        "http://remnawave-ssh-proxy:8080?token=secret",
    ],
)
def test_node_ssh_requires_dedicated_safe_broker_origin(broker_url: str) -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_NODE_SSH_BROKER_URL"):
        _settings(
            remnawave_node_ssh_enabled=True,
            remnawave_node_ssh_broker_url=broker_url,
            remnawave_node_ssh_broker_secret=SecretStr("a" * 128),
            remnawave_node_ssh_trusted_admin_ids=str(uuid4()),
            remnawave_node_ssh_allowed_node_ids=str(uuid4()),
            passkey_enabled=True,
            passkey_admin_enabled=True,
        )
