from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.exc import MultipleResultsFound

from src.application.services.remnawave_identity_access import resolve_exact_mapped_remnawave_ref
from src.application.services.remnawave_identity_retirement import RemnawaveOwnerIdentityRetirementPlan
from src.application.use_cases.mobile_auth import delete_account as delete_account_module
from src.application.use_cases.mobile_auth.delete_account import MobileDeleteAccountUseCase
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveMutationAcceptedPending


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
    def __init__(self, *, delete_error: Exception | None = None, absent_after_delete: bool = True):
        self.deleted = []
        self.confirmed = []
        self.delete_error = delete_error
        self.absent_after_delete = absent_after_delete

    async def delete(self, remnawave_ref):
        self.deleted.append(remnawave_ref)
        if self.delete_error is not None:
            raise self.delete_error

    async def confirm_absent_by_id(self, remnawave_user_id: int) -> bool:
        self.confirmed.append(remnawave_user_id)
        return self.absent_after_delete


class FakeRedis:
    async def hgetall(self, _key):
        return {}

    async def delete(self, *_keys):
        return len(_keys)


class _ReconciliationResult:
    def __init__(self, value, *, duplicate: bool = False):
        self.value = value
        self.duplicate = duplicate

    def scalar_one_or_none(self):
        if self.duplicate:
            raise MultipleResultsFound()
        return self.value

    def scalars(self):
        return self

    def all(self):
        if self.value is None:
            return []
        return [self.value, self.value] if self.duplicate else [self.value]


class FakeIdentitySession:
    def __init__(self, reconciliation=None, *, duplicate: bool = False):
        self.reconciliation = reconciliation
        self.duplicate = duplicate
        self.retired = []

    async def execute(self, _statement):
        return _ReconciliationResult(self.reconciliation, duplicate=self.duplicate)


@pytest.fixture(autouse=True)
def _use_in_memory_identity_retirement(monkeypatch):
    async def prepare(session, *, customer):
        user_ref = await resolve_exact_mapped_remnawave_ref(
            session,
            subject_type="mobile_user",
            subject_id=customer.id,
            numeric_user_id=customer.remnawave_user_id,
            legacy_uuid_raw=customer.remnawave_uuid,
        )
        return RemnawaveOwnerIdentityRetirementPlan(
            customer=customer,
            user_ref=user_ref,
            provider_refs=(user_ref,) if user_ref is not None else (),
            service_identities=(),
            reconciliations=(),
            active_grants=(),
        )

    async def apply(session, *, plan, retired_at):
        session.retired.append((plan, retired_at))

    monkeypatch.setattr(delete_account_module, "prepare_remnawave_owner_identity_retirement", prepare)
    monkeypatch.setattr(delete_account_module, "apply_remnawave_owner_identity_retirement", apply)


def _mapped_identity(user, *, numeric_id: int | None = None, legacy_uuid: str | None = None, state="mapped"):
    return SimpleNamespace(
        subject_type="mobile_user",
        subject_id=user.id,
        reconciliation_state=state,
        numeric_user_id=numeric_id if numeric_id is not None else user.remnawave_user_id,
        legacy_uuid=legacy_uuid if legacy_uuid is not None else user.remnawave_uuid,
    )


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
        remnawave_user_id=73,
        remnawave_uuid=str(remnawave_uuid),
        subscription_auto_renew_enabled=True,
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
        session=FakeIdentitySession(_mapped_identity(user)),
        user_repo=repo,
        user_gateway=gateway,
        redis_client=FakeRedis(),
    ).execute(user_id)

    assert result.vpn_access_removed is True
    assert gateway.deleted == [RemnawaveUserRef(id=73, legacy_uuid=remnawave_uuid)]
    assert repo.updated == [user]
    assert user.email == f"deleted-{str(user_id).replace('-', '')}@deleted.cyber-vpn.net"
    assert user.telegram_id is None
    assert user.telegram_subject is None
    assert user.remnawave_uuid is None
    assert user.remnawave_user_id is None
    assert user.subscription_auto_renew_enabled is False
    assert user.subscription_url is None
    assert user.referral_code is None
    assert user.is_active is False
    assert user.status == "deleted"


def _mobile_user(*, remnawave_user_id: int | None, remnawave_uuid) -> SimpleNamespace:
    user_id = uuid4()
    return SimpleNamespace(
        id=user_id,
        email="customer@example.test",
        password_hash="hash",
        username="customer",
        telegram_subject=None,
        telegram_id=None,
        telegram_username=None,
        notification_prefs={},
        totp_secret=None,
        totp_enabled=False,
        remnawave_user_id=remnawave_user_id,
        remnawave_uuid=str(remnawave_uuid) if remnawave_uuid is not None else None,
        subscription_auto_renew_enabled=False,
        subscription_url=None,
        referral_code=None,
        is_partner=False,
        partner_promoted_at=None,
        partner_account_id=None,
        partner_user_id=None,
        referred_by_user_id=None,
        trial_activated_at=None,
        trial_expires_at=None,
        is_active=True,
        status="active",
        updated_at=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_account_rejects_legacy_only_identity_without_local_anonymization():
    user = _mobile_user(remnawave_user_id=None, remnawave_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    gateway = FakeRemnawaveUserGateway()

    with pytest.raises(RuntimeError, match="numeric identity is incomplete"):
        await MobileDeleteAccountUseCase(
            session=FakeIdentitySession(),
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)

    assert repo.updated == []
    assert user.is_active is True
    assert user.remnawave_uuid is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_404_requires_numeric_absence_confirmation_before_clearing_refs():
    user = _mobile_user(remnawave_user_id=73, remnawave_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    request = httpx.Request("DELETE", "https://remnawave.test/api/users/73")
    delete_404 = httpx.HTTPStatusError(
        "missing",
        request=request,
        response=httpx.Response(404, request=request),
    )
    gateway = FakeRemnawaveUserGateway(delete_error=delete_404, absent_after_delete=False)

    with pytest.raises(httpx.HTTPStatusError):
        await MobileDeleteAccountUseCase(
            session=FakeIdentitySession(_mapped_identity(user)),
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)

    assert gateway.confirmed == [73]
    assert repo.updated == []
    assert user.is_active is True
    assert user.remnawave_user_id == 73


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_404_allows_anonymization_only_after_confirmed_numeric_absence():
    user = _mobile_user(remnawave_user_id=73, remnawave_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    request = httpx.Request("DELETE", "https://remnawave.test/api/users/73")
    delete_404 = httpx.HTTPStatusError(
        "missing",
        request=request,
        response=httpx.Response(404, request=request),
    )
    gateway = FakeRemnawaveUserGateway(delete_error=delete_404, absent_after_delete=True)

    result = await MobileDeleteAccountUseCase(
        session=FakeIdentitySession(_mapped_identity(user)),
        user_repo=repo,
        user_gateway=gateway,
        redis_client=FakeRedis(),
    ).execute(user.id)

    assert result.vpn_access_removed is True
    assert gateway.confirmed == [73]
    assert repo.updated == [user]
    assert user.remnawave_user_id is None
    assert user.remnawave_uuid is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_accepted_but_unconfirmed_never_anonymizes_local_account():
    user = _mobile_user(remnawave_user_id=73, remnawave_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    gateway = FakeRemnawaveUserGateway(
        delete_error=RemnawaveMutationAcceptedPending(operation="delete", numeric_user_id=73)
    )

    with pytest.raises(RemnawaveMutationAcceptedPending):
        await MobileDeleteAccountUseCase(
            session=FakeIdentitySession(_mapped_identity(user)),
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)

    assert repo.updated == []
    assert user.is_active is True
    assert user.remnawave_user_id == 73
    assert user.remnawave_uuid is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_distinct_provider_pairs_stops_before_local_retirement_on_second_failure(
    monkeypatch,
):
    user = _mobile_user(remnawave_user_id=73, remnawave_uuid=uuid4())
    first_ref = RemnawaveUserRef(id=73, legacy_uuid=UUID(user.remnawave_uuid))
    second_ref = RemnawaveUserRef(id=74, legacy_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    request = httpx.Request("DELETE", "https://remnawave.test/api/users/74")
    second_error = httpx.HTTPStatusError(
        "provider failure",
        request=request,
        response=httpx.Response(503, request=request),
    )

    class _SecondDeleteFails(FakeRemnawaveUserGateway):
        async def delete(self, remnawave_ref):
            self.deleted.append(remnawave_ref)
            if remnawave_ref == second_ref:
                raise second_error

    async def prepare(_session, *, customer):
        return RemnawaveOwnerIdentityRetirementPlan(
            customer=customer,
            user_ref=first_ref,
            provider_refs=(first_ref, second_ref),
            service_identities=(),
            reconciliations=(),
            active_grants=(),
        )

    monkeypatch.setattr(delete_account_module, "prepare_remnawave_owner_identity_retirement", prepare)
    gateway = _SecondDeleteFails()
    session = FakeIdentitySession()

    with pytest.raises(httpx.HTTPStatusError):
        await MobileDeleteAccountUseCase(
            session=session,
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)

    assert gateway.deleted == [first_ref, second_ref]
    assert session.retired == []
    assert repo.updated == []
    assert user.status == "active"
    assert user.remnawave_user_id == 73
    assert user.remnawave_uuid is not None


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("state", [None, "pending", "conflict"])
async def test_mobile_delete_account_fails_closed_without_exact_mapped_ledger(state):
    user = _mobile_user(remnawave_user_id=73, remnawave_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    gateway = FakeRemnawaveUserGateway()
    reconciliation = None if state is None else _mapped_identity(user, state=state)

    with pytest.raises(RuntimeError, match="reconciliation"):
        await MobileDeleteAccountUseCase(
            session=FakeIdentitySession(reconciliation),
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)

    assert gateway.deleted == []
    assert repo.updated == []
    assert user.is_active is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mobile_delete_account_rejects_wrong_or_duplicate_mapping_before_provider_delete():
    user = _mobile_user(remnawave_user_id=73, remnawave_uuid=uuid4())
    repo = FakeMobileUserRepository(user)
    gateway = FakeRemnawaveUserGateway()

    with pytest.raises(RuntimeError, match="reconciliation"):
        await MobileDeleteAccountUseCase(
            session=FakeIdentitySession(_mapped_identity(user, numeric_id=74)),
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)
    with pytest.raises(RuntimeError, match="not unique"):
        await MobileDeleteAccountUseCase(
            session=FakeIdentitySession(_mapped_identity(user), duplicate=True),
            user_repo=repo,
            user_gateway=gateway,
            redis_client=FakeRedis(),
        ).execute(user.id)

    assert gateway.deleted == []
    assert repo.updated == []
