"""Unit tests for auth API schemas."""

from src.presentation.api.v1.auth.schemas import LoginRequest


class TestLoginRequestSchema:
    """Keep login payload compatibility aligned across web clients."""

    def test_accepts_canonical_login_or_email_field(self) -> None:
        request = LoginRequest.model_validate(
            {"login_or_email": "neo@cybervpn.io", "password": "secret"}
        )

        assert request.login_or_email == "neo@cybervpn.io"

    def test_accepts_legacy_email_alias_for_backward_compatibility(self) -> None:
        request = LoginRequest.model_validate(
            {"email": "neo@cybervpn.io", "password": "secret"}
        )

        assert request.login_or_email == "neo@cybervpn.io"
