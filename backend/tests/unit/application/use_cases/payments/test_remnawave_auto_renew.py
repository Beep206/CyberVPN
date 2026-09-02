from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.payments import remnawave_auto_renew as module
from src.application.use_cases.payments.remnawave_auto_renew import (
    CreateRemnawaveAutoRenewInvoiceUseCase,
    RemnawaveAutoRenewConflictError,
    _expiry_digest,
)


class _ScalarResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self) -> list[object]:
        return [] if self._value is None else [self._value]


def _reconciliation(
    customer_id,
    *,
    numeric_user_id: int = 42,
    legacy_uuid=None,
    state: str = "mapped",
) -> SimpleNamespace:
    return SimpleNamespace(
        subject_type="mobile_user",
        subject_id=customer_id,
        reconciliation_state=state,
        numeric_user_id=numeric_user_id,
        legacy_uuid=None if legacy_uuid is None else str(legacy_uuid),
    )


@pytest.mark.unit
async def test_auto_renew_uses_cybervpn_plan_and_provider_reconciliation(monkeypatch) -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    plan_id = uuid4()
    payment_id = uuid4()
    expires_at = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
        subscription_auto_renew_enabled=True,
        is_active=True,
        telegram_id=555001,
        username="local-user",
        telegram_username="local-telegram",
    )
    previous_payment = SimpleNamespace(
        plan_id=plan_id,
        subscription_days=30,
        currency="USD",
        metadata_={"channel": "web"},
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.side_effect = [
        _ScalarResult(customer),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
        _ScalarResult(previous_payment),
    ]
    gateway = AsyncMock()
    gateway.get_by_ref.return_value = SimpleNamespace(
        remnawave_id=42,
        uuid=legacy_uuid,
        expires_at=expires_at,
        telegram_id=999999,
        username="provider-controlled",
    )
    quote = SimpleNamespace(plan_name="Monthly")

    checkout = AsyncMock()
    checkout.execute.return_value = quote
    monkeypatch.setattr(module, "CheckoutUseCase", lambda _session: checkout)
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)
    commit = AsyncMock()
    commit.execute.return_value = SimpleNamespace(
        payment=SimpleNamespace(id=payment_id, metadata_={}),
        invoice=SimpleNamespace(payment_url="https://pay.example/invoice", amount="10.00", currency="USD"),
        reused=True,
    )
    monkeypatch.setattr(module, "CommitCheckoutUseCase", lambda _session, _client: commit)
    monkeypatch.setattr(module, "_utc_now", lambda: datetime(2026, 8, 30, 12, 0, tzinfo=UTC))
    session.get.return_value = None

    key = f"remnawave:auto-renew:42:{_expiry_digest(expires_at)}"
    result = await CreateRemnawaveAutoRenewInvoiceUseCase(
        session,
        crypto_client=AsyncMock(),
        user_gateway=gateway,
    ).execute(
        remnawave_user_id=42,
        expected_expire_at=expires_at,
        idempotency_key=key,
    )

    assert result.payment_id == str(payment_id)
    assert result.reused is True
    assert result.notification_status == "queued"
    assert commit.execute.await_args.kwargs["payment_plan_id"] == plan_id
    assert commit.execute.await_args.kwargs["reconcile_provider_by_payload"] is True
    assert commit.execute.await_args.kwargs["metadata_extra"]["remnawave_user_id"] == 42
    queued = session.add.call_args.args[0]
    assert queued.telegram_id == 555001
    assert queued.notification_type == f"auto_renew:{customer.id}"
    assert "local-user" in queued.message
    assert "provider-controlled" not in queued.message
    assert "999999" not in queued.message
    session.commit.assert_awaited_once()


@pytest.mark.unit
async def test_auto_renew_fails_closed_when_upstream_expiry_changed(monkeypatch) -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    expected = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.side_effect = [
        _ScalarResult(
            SimpleNamespace(
                id=customer_id,
                remnawave_user_id=42,
                remnawave_uuid=str(legacy_uuid),
                subscription_auto_renew_enabled=True,
                is_active=True,
                telegram_id=555001,
            )
        ),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
    ]
    gateway = AsyncMock()
    gateway.get_by_ref.return_value = SimpleNamespace(
        remnawave_id=42,
        uuid=legacy_uuid,
        expires_at=datetime(2026, 9, 30, 12, 30, tzinfo=UTC),
    )
    key = f"remnawave:auto-renew:42:{_expiry_digest(expected)}"
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="expiry changed"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=key,
        )

    session.commit.assert_not_awaited()


@pytest.mark.unit
async def test_auto_renew_rejects_misrouted_upstream_numeric_identity(monkeypatch) -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    expected = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(
            SimpleNamespace(
                id=customer_id,
                remnawave_user_id=42,
                remnawave_uuid=str(legacy_uuid),
                subscription_auto_renew_enabled=True,
                is_active=True,
                telegram_id=555001,
            )
        ),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
    ]
    gateway = AsyncMock()
    gateway.get_by_ref.return_value = SimpleNamespace(remnawave_id=99, uuid=legacy_uuid, expires_at=expected)
    key = f"remnawave:auto-renew:42:{_expiry_digest(expected)}"
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="upstream identity"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=key,
        )

    session.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "reconciliation",
    [
        None,
        SimpleNamespace(reconciliation_state="pending", numeric_user_id=42, legacy_uuid=None),
        SimpleNamespace(reconciliation_state="mapped", numeric_user_id=99, legacy_uuid=None),
    ],
)
async def test_auto_renew_requires_exact_mapped_numeric_identity(monkeypatch, reconciliation) -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    expected = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    if reconciliation is not None:
        reconciliation.subject_type = "mobile_user"
        reconciliation.subject_id = customer_id
        reconciliation.legacy_uuid = str(legacy_uuid)
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(
            SimpleNamespace(
                id=customer_id,
                remnawave_user_id=42,
                remnawave_uuid=str(legacy_uuid),
                subscription_auto_renew_enabled=True,
            )
        ),
        _ScalarResult(reconciliation),
    ]
    gateway = AsyncMock()
    key = f"remnawave:auto-renew:42:{_expiry_digest(expected)}"
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="reconciliation is incomplete"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=key,
        )

    gateway.get_by_ref.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize("local_legacy_uuid", [None, "not-a-uuid"])
async def test_auto_renew_rejects_missing_reconciliation_or_invalid_local_legacy_identity(
    monkeypatch, local_legacy_uuid
) -> None:
    customer_id = uuid4()
    expected = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(
            SimpleNamespace(
                id=customer_id,
                remnawave_user_id=42,
                remnawave_uuid=local_legacy_uuid,
                subscription_auto_renew_enabled=True,
            )
        ),
        _ScalarResult(None),
    ]
    gateway = AsyncMock()
    key = f"remnawave:auto-renew:42:{_expiry_digest(expected)}"
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="reconciliation is incomplete"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=key,
        )

    gateway.get_by_ref.assert_not_awaited()


@pytest.mark.unit
async def test_auto_renew_rejects_split_brain_legacy_identity(monkeypatch) -> None:
    customer_id = uuid4()
    expected = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(
            SimpleNamespace(
                id=customer_id,
                remnawave_user_id=42,
                remnawave_uuid=str(uuid4()),
                subscription_auto_renew_enabled=True,
            )
        ),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=uuid4())),
    ]
    gateway = AsyncMock()
    key = f"remnawave:auto-renew:42:{_expiry_digest(expected)}"
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="reconciliation is incomplete"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=key,
        )

    gateway.get_by_ref.assert_not_awaited()


@pytest.mark.unit
async def test_auto_renew_rejects_upstream_legacy_identity_mismatch_before_billing(monkeypatch) -> None:
    customer_id = uuid4()
    legacy_uuid = uuid4()
    expected = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
        subscription_auto_renew_enabled=True,
        is_active=True,
        telegram_id=555001,
    )
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(customer),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
    ]
    gateway = AsyncMock()
    gateway.get_by_ref.side_effect = module.RemnawaveIdentityBindingError("legacy mismatch")
    checkout = AsyncMock()
    monkeypatch.setattr(module, "CheckoutUseCase", lambda _session: checkout)
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="upstream identity"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=f"remnawave:auto-renew:42:{_expiry_digest(expected)}",
        )

    checkout.execute.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.unit
async def test_auto_renew_rejects_indefinitely_expired_user_before_billing(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    expected = now - timedelta(hours=2, seconds=1)
    customer_id = uuid4()
    legacy_uuid = uuid4()
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(
            SimpleNamespace(
                id=customer_id,
                remnawave_user_id=42,
                remnawave_uuid=str(legacy_uuid),
                subscription_auto_renew_enabled=True,
                is_active=True,
                telegram_id=555001,
            )
        ),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
    ]
    gateway = AsyncMock()
    gateway.get_by_ref.return_value = SimpleNamespace(
        remnawave_id=42,
        uuid=legacy_uuid,
        expires_at=expected,
    )
    checkout = AsyncMock()
    monkeypatch.setattr(module, "CheckoutUseCase", lambda _session: checkout)
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)
    monkeypatch.setattr(module, "_utc_now", lambda: now)

    with pytest.raises(RemnawaveAutoRenewConflictError, match="renewal window"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            session,
            crypto_client=AsyncMock(),
            user_gateway=gateway,
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expected,
            idempotency_key=f"remnawave:auto-renew:42:{_expiry_digest(expected)}",
        )

    checkout.execute.assert_not_awaited()


@pytest.mark.unit
async def test_auto_renew_replay_does_not_duplicate_canonical_notification(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    expected = now + timedelta(minutes=30)
    customer_id = uuid4()
    legacy_uuid = uuid4()
    payment_id = uuid4()
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=str(legacy_uuid),
        subscription_auto_renew_enabled=True,
        is_active=True,
        telegram_id=555001,
        username="local-user",
        telegram_username=None,
    )
    previous_payment = SimpleNamespace(
        plan_id=uuid4(),
        subscription_days=30,
        currency="USD",
        metadata_={"channel": "web"},
    )
    payment = SimpleNamespace(id=payment_id, metadata_={})
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.side_effect = [
        _ScalarResult(customer),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
        _ScalarResult(previous_payment),
        _ScalarResult(customer),
        _ScalarResult(_reconciliation(customer_id, legacy_uuid=legacy_uuid)),
        _ScalarResult(previous_payment),
    ]
    session.get.return_value = None
    gateway = AsyncMock()
    gateway.get_by_ref.return_value = SimpleNamespace(remnawave_id=42, uuid=legacy_uuid, expires_at=expected)
    monkeypatch.setattr(module.settings, "payment_autorenewal_enabled", True)
    monkeypatch.setattr(module, "_utc_now", lambda: now)
    monkeypatch.setattr(
        module,
        "CheckoutUseCase",
        lambda _session: SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(plan_name="Monthly"))),
    )
    commit = AsyncMock()
    commit.execute.return_value = SimpleNamespace(
        payment=payment,
        invoice=SimpleNamespace(payment_url="https://pay.example/invoice", amount="10.00", currency="USD"),
        reused=True,
    )
    monkeypatch.setattr(module, "CommitCheckoutUseCase", lambda _session, _client: commit)
    use_case = CreateRemnawaveAutoRenewInvoiceUseCase(
        session,
        crypto_client=AsyncMock(),
        user_gateway=gateway,
    )
    kwargs = {
        "remnawave_user_id": 42,
        "expected_expire_at": expected,
        "idempotency_key": f"remnawave:auto-renew:42:{_expiry_digest(expected)}",
    }

    first = await use_case.execute(**kwargs)
    second = await use_case.execute(**kwargs)

    assert first.notification_status == "queued"
    assert second.notification_status == "already_queued"
    assert session.add.call_count == 1


@pytest.mark.unit
async def test_auto_renew_rejects_idempotency_key_for_other_expiry() -> None:
    expires_at = datetime(2026, 8, 30, 12, 30, tzinfo=UTC)
    wrong = datetime(2026, 8, 30, 12, 31, tzinfo=UTC)
    key = f"remnawave:auto-renew:42:{_expiry_digest(wrong)}"

    with pytest.raises(ValueError, match="does not match"):
        await CreateRemnawaveAutoRenewInvoiceUseCase(
            AsyncMock(),
            crypto_client=AsyncMock(),
            user_gateway=AsyncMock(),
        ).execute(
            remnawave_user_id=42,
            expected_expire_at=expires_at,
            idempotency_key=key,
        )
