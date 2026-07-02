from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix
from src.application.use_cases.growth_codes.registry import _invite_shadow_usage
from src.application.use_cases.invites.redeem_invite import RedeemInviteUseCase, _ensure_shadow_invite_redeemable
from src.domain.enums import InviteSource
from src.domain.exceptions import InviteCodeAlreadyUsedError, InviteCodeExhaustedError, InviteCodeNotFoundError
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.presentation.dependencies.auth_realms import RealmResolution


class _MissingInviteRepo:
    async def get_by_code_for_update(self, _code: str):
        return None

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
    assert record.__dict__["code_prefix"] == build_growth_code_prefix(raw_code)
    assert record.__dict__["code_length"] == len(raw_code)
    assert raw_code not in str(record.__dict__)


def test_shadow_capacity_preflight_blocks_consumed_single_use_invite() -> None:
    now = datetime.now(UTC)
    invite = InviteCodeModel(
        code="SINGLESTUCK1",
        owner_user_id=UUID("00000000-0000-0000-0000-000000000301"),
        free_days=7,
        source=InviteSource.ADMIN_GRANT,
        expires_at=now + timedelta(days=7),
        usage_mode="single_use",
        is_used=False,
        redeemed_count=0,
        active_redemptions_count=0,
        status="active",
    )
    shadow_code = GrowthCodeModel(
        code_hash="hash",
        code_prefix="prefix",
        code_type="invite",
        status="redeemed",
        issuer_type="admin",
        max_uses=1,
        uses_count=1,
    )

    with pytest.raises(InviteCodeAlreadyUsedError):
        _ensure_shadow_invite_redeemable(invite=invite, shadow_code=shadow_code)


def test_invite_shadow_usage_preserves_multi_use_capacity_from_legacy_invite() -> None:
    now = datetime.now(UTC)
    invite = InviteCodeModel(
        code="MULTICAPACITY1",
        owner_user_id=UUID("00000000-0000-0000-0000-000000000303"),
        free_days=7,
        source=InviteSource.ADMIN_GRANT,
        expires_at=now + timedelta(days=7),
        usage_mode="multi_use",
        max_redemptions=3,
        redeemed_count=1,
        active_redemptions_count=1,
        status="active",
    )

    status, max_uses, uses_count = _invite_shadow_usage(
        invite=invite,
        now=now,
        existing_uses_count=1,
    )

    assert status == "active"
    assert max_uses == 3
    assert uses_count == 1


def test_shadow_capacity_preflight_blocks_exhausted_multi_use_invite() -> None:
    now = datetime.now(UTC)
    invite = InviteCodeModel(
        code="MULTISTUCK1",
        owner_user_id=UUID("00000000-0000-0000-0000-000000000302"),
        free_days=7,
        source=InviteSource.ADMIN_GRANT,
        expires_at=now + timedelta(days=7),
        usage_mode="multi_use",
        max_redemptions=2,
        redeemed_count=2,
        active_redemptions_count=2,
        status="exhausted",
    )
    shadow_code = GrowthCodeModel(
        code_hash="hash",
        code_prefix="prefix",
        code_type="invite",
        status="exhausted",
        issuer_type="admin",
        max_uses=2,
        uses_count=2,
    )

    with pytest.raises(InviteCodeExhaustedError):
        _ensure_shadow_invite_redeemable(invite=invite, shadow_code=shadow_code)
