from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.mobile_auth.delete_account import MobileDeleteAccountUseCase


class FakeMobileUserRepository:
    def __init__(self, user):
        self.user = user
        self.updated = []

    async def get_by_id(self, user_id):
        return self.user if self.user.id == user_id else None

    async def update(self, user):
        self.updated.append(user)
        return user


class FakeRemnawaveUserGateway:
    def __init__(self):
        self.deleted = []

    async def delete(self, remnawave_uuid):
        self.deleted.append(remnawave_uuid)


class FakeRedis:
    async def hgetall(self, _key):
        return {}

    async def delete(self, *_keys):
        return len(_keys)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_account_anonymizes_user_and_removes_vpn_access():
    user_id = uuid4()
    remnawave_uuid = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="customer@example.test",
        password_hash="hash",
        username="customer",
        telegram_subject="telegram:123",
        telegram_id=123,
        telegram_username="customer_tg",
        notification_prefs={"telegram": True},
        totp_secret="secret",
        totp_enabled=True,
        remnawave_uuid=str(remnawave_uuid),
        subscription_url="https://sub.example.test/redacted",
        referral_code="ABC123",
        is_partner=True,
        partner_promoted_at="2026-05-21",
        partner_account_id=uuid4(),
        partner_user_id=uuid4(),
        referred_by_user_id=uuid4(),
        trial_activated_at="2026-05-21",
        trial_expires_at="2026-05-24",
        is_active=True,
        status="active",
        updated_at=None,
    )
    repo = FakeMobileUserRepository(user)
    gateway = FakeRemnawaveUserGateway()

    result = await MobileDeleteAccountUseCase(
        user_repo=repo,
        user_gateway=gateway,
        redis_client=FakeRedis(),
    ).execute(user_id)

    assert result.vpn_access_removed is True
    assert gateway.deleted == [remnawave_uuid]
    assert repo.updated == [user]
    assert user.email == f"deleted-{str(user_id).replace('-', '')}@deleted.cyber-vpn.net"
    assert user.telegram_id is None
    assert user.telegram_subject is None
    assert user.remnawave_uuid is None
    assert user.subscription_url is None
    assert user.referral_code is None
    assert user.is_active is False
    assert user.status == "deleted"
