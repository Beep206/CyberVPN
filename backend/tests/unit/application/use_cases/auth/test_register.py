"""Unit tests for RegisterUseCase."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.auth.register import RegisterUseCase
from src.domain.exceptions import DuplicateUsernameError


def _user(*, active: bool = False, verified: bool = False) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.login = "veephtc"
    user.email = "veephtc@gmail.com"
    user.is_active = active
    user.is_email_verified = verified
    return user


@pytest.mark.unit
async def test_resume_unverified_email_registration_resends_otp_without_new_user() -> None:
    existing = _user()
    otp = MagicMock()
    otp.code = "123456"

    user_repo = AsyncMock()
    user_repo.get_by_login.return_value = existing
    user_repo.get_by_email.return_value = existing

    auth_service = AsyncMock()
    otp_service = AsyncMock()
    otp_service.resend_existing_otp.return_value = otp
    email_dispatcher = AsyncMock()

    use_case = RegisterUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        otp_service=otp_service,
        email_dispatcher=email_dispatcher,
    )

    result = await use_case.execute(
        login="veephtc",
        email="veephtc@gmail.com",
        password="Stage1StrongPassword123!",
        tos_accepted=True,
        locale="ru-RU",
    )

    assert result.user == existing
    assert result.otp_sent is True
    assert result.resumed_unverified_registration is True
    user_repo.create.assert_not_called()
    auth_service.hash_password.assert_not_called()
    otp_service.resend_existing_otp.assert_awaited_once_with(
        user_id=existing.id,
        purpose="email_verification",
    )
    email_dispatcher.dispatch_otp_email.assert_awaited_once_with(
        email="veephtc@gmail.com",
        otp_code="123456",
        locale="ru-RU",
        is_resend=True,
    )


@pytest.mark.unit
async def test_verified_duplicate_email_still_rejects_registration() -> None:
    existing = _user(active=True, verified=True)
    user_repo = AsyncMock()
    user_repo.get_by_login.return_value = existing
    user_repo.get_by_email.return_value = existing

    use_case = RegisterUseCase(
        user_repo=user_repo,
        auth_service=AsyncMock(),
        otp_service=AsyncMock(),
        email_dispatcher=AsyncMock(),
    )

    with pytest.raises(DuplicateUsernameError):
        await use_case.execute(
            login="veephtc",
            email="veephtc@gmail.com",
            password="Stage1StrongPassword123!",
            tos_accepted=True,
            locale="ru-RU",
        )
