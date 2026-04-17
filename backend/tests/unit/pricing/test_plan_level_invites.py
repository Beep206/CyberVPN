from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.invites.generate_invites import (
    GenerateInvitesForPaymentUseCase,
)
from src.domain.enums import InviteSource


@pytest.mark.asyncio
async def test_generate_invites_uses_plan_bundle() -> None:
    owner_user_id = uuid4()
    plan_id = uuid4()
    payment_id = uuid4()

    invite_repo = SimpleNamespace(create_batch=AsyncMock(side_effect=lambda models: models))
    plan_repo = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                invite_bundle={"count": 2, "friend_days": 14, "expiry_days": 60},
            )
        )
    )

    use_case = GenerateInvitesForPaymentUseCase(invite_repo=invite_repo, plan_repo=plan_repo)
    invites = await use_case.execute(
        owner_user_id=owner_user_id,
        plan_id=plan_id,
        payment_id=payment_id,
    )

    assert len(invites) == 2
    assert all(invite.owner_user_id == owner_user_id for invite in invites)
    assert all(invite.plan_id == plan_id for invite in invites)
    assert all(invite.source == InviteSource.PURCHASE for invite in invites)
    assert all(invite.free_days == 14 for invite in invites)
    assert all(invite.source_payment_id == payment_id for invite in invites)
    assert all(invite.expires_at is not None for invite in invites)


@pytest.mark.asyncio
async def test_generate_invites_returns_empty_when_bundle_disabled() -> None:
    invite_repo = SimpleNamespace(create_batch=AsyncMock())
    plan_repo = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                invite_bundle={"count": 0, "friend_days": 0, "expiry_days": 0},
            )
        )
    )

    use_case = GenerateInvitesForPaymentUseCase(invite_repo=invite_repo, plan_repo=plan_repo)
    invites = await use_case.execute(
        owner_user_id=uuid4(),
        plan_id=uuid4(),
        payment_id=uuid4(),
    )

    assert invites == []
    invite_repo.create_batch.assert_not_called()
