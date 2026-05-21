from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.trial.stage1_trial_provisioning import Stage1TrialProvisioningResult
from src.presentation.api.v1.invites import routes as invite_routes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provision_redeemed_invite_access_updates_mobile_user(monkeypatch):
    user_id = uuid4()
    entitlement_grant_id = uuid4()
    expires_at = datetime(2026, 5, 28, 13, 40, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        email="tg123456@telegram.local",
        username="telegram-user",
        telegram_id=123456,
        remnawave_uuid=None,
        subscription_url=None,
    )
    updated_users = []
    seen_requests = []

    class FakeDb:
        async def get(self, model, item_id):
            assert model is invite_routes.EntitlementGrantModel
            assert item_id == entitlement_grant_id
            return SimpleNamespace(expires_at=expires_at)

    class FakeMobileUserRepository:
        def __init__(self, _db):
            pass

        async def get_by_id(self, item_id):
            assert item_id == user_id
            return user

        async def update(self, item):
            updated_users.append(item)
            return item

    class FakeProvisioningGateway:
        async def provision_trial_access(self, request):
            seen_requests.append(request)
            return Stage1TrialProvisioningResult(
                customer_account_id=request.customer_account_id,
                remnawave_uuid="2f4a8f2d-e8a5-4a2f-9c70-ef6e35b3a601",
                profile_id=request.profile_id,
                status="active",
                expires_at=request.trial_expires_at,
                subscription_url="https://sub.example.com/redacted",
                created=True,
            )

    monkeypatch.setattr(invite_routes, "MobileUserRepository", FakeMobileUserRepository)

    await invite_routes._provision_redeemed_invite_access(
        db=FakeDb(),
        user_id=user_id,
        result=SimpleNamespace(
            entitlement_grant_id=entitlement_grant_id,
            invite=SimpleNamespace(free_days=7),
        ),
        provisioning_gateway=FakeProvisioningGateway(),
    )

    assert seen_requests[0].customer_account_id == user_id
    assert seen_requests[0].trial_expires_at == expires_at
    assert user.remnawave_uuid == "2f4a8f2d-e8a5-4a2f-9c70-ef6e35b3a601"
    assert user.subscription_url == "https://sub.example.com/redacted"
    assert updated_users == [user]
