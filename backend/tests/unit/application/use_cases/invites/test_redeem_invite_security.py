from __future__ import annotations

import logging
from uuid import UUID

import pytest

from src.application.use_cases.invites.redeem_invite import RedeemInviteUseCase
from src.domain.exceptions import InviteCodeNotFoundError
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.presentation.dependencies.auth_realms import RealmResolution


class _MissingInviteRepo:
    async def get_by_code(self, _code: str):
        return None


@pytest.mark.asyncio
async def test_redeem_invite_not_found_log_uses_redacted_code_ref(caplog: pytest.LogCaptureFixture) -> None:
    raw_code = "GI-SENSITIVE-RAW-CODE-42"
    use_case = RedeemInviteUseCase(session=object())
    use_case._invite_repo = _MissingInviteRepo()  # type: ignore[attr-defined]

    with caplog.at_level(logging.WARNING):
        with pytest.raises(InviteCodeNotFoundError):
            await use_case.execute(
                code=raw_code,
                user_id=UUID("00000000-0000-0000-0000-000000000101"),
                current_realm=RealmResolution(
                    auth_realm=AuthRealmModel(
                        id=UUID("00000000-0000-0000-0000-000000000202"),
                        realm_key="customer",
                        realm_type="customer",
                        display_name="Customer",
                        audience="customer",
                        cookie_namespace="customer",
                        is_default=True,
                    ),
                    source="test",
                ),
            )

    record = next(item for item in caplog.records if item.message == "invite_redeem_not_found")
    assert "code" not in record.__dict__
    assert record.__dict__["code_prefix"] == "GI-SENSI"
    assert record.__dict__["code_length"] == len(raw_code)
    assert raw_code not in str(record.__dict__)
