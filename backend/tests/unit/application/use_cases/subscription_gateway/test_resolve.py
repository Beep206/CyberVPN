from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.vpn_product_readiness import (
    PRODUCT_PLAN_MISMATCH_REASON,
    TASK2_READINESS_MANIFEST_MISMATCH_REASON,
    TASK2_READINESS_SIGNATURE_INVALID_REASON,
)
from src.application.use_cases.subscription_gateway.resolve import (
    EXTERNAL_SQUAD_MISMATCH_REASON,
    PREMIUM_SMART_RU_XRAY_FAILOVER_CANARY_CONTEXT_KEY,
    ResolveSubscriptionProductUseCase,
    SubscriptionGatewayNotFoundError,
    SubscriptionGatewayUnavailableError,
)
from src.config.settings import settings
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.remnawave.client import RemnawaveClient
from tests.helpers.spb_de_readiness import (
    enable_spb_de_readiness,
    make_spb_de_readiness_attestation,
    manifest_pointer_json,
)

OVERLAPPING_PLAN_CODES = "premium_smart_ru,premium_spb_de_exceptions"
SMART_RU_EXTERNAL_SQUAD_UUID = "409147a7-a03c-4db5-bccf-33d3caaf8d52"
TASK2_EXTERNAL_SQUAD_UUID = "ed139a4b-d21f-478a-b1d2-73ce9d9012ea"
PROVIDER_NUMERIC_SUBJECT_ID = 4201
PROVIDER_SUBJECT_REF = "e131349d-1d45-4a21-ac66-4e98fa54c22d"
EXPECTED_EXTERNAL_SQUAD_UUIDS = {
    "premium_smart_ru": SMART_RU_EXTERNAL_SQUAD_UUID,
    "premium_spb_de_exceptions": TASK2_EXTERNAL_SQUAD_UUID,
}


class _RemnawaveClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.paths: list[str] = []

    async def get(self, path: str):
        self.paths.append(path)
        return self.payload


class _Repository:
    def __init__(self, identities: list[SimpleNamespace], grants: dict[object, SimpleNamespace | None]) -> None:
        self.identities = identities
        self.grants = grants
        self.grant_checks: list[object] = []

    async def list_active_subscription_identities_by_provider_numeric_subject(self, **kwargs):
        assert kwargs == {
            "provider_name": "remnawave",
            "provider_numeric_subject_id": 4201,
        }
        return self.identities

    async def get_active_entitlement_grant_for_service_identity(self, *, service_identity_id, now):
        assert now.tzinfo is not None
        self.grant_checks.append(service_identity_id)
        return self.grants.get(service_identity_id)


class _LedgerResult:
    def __init__(self, reconciliation: SimpleNamespace | None) -> None:
        self._reconciliation = reconciliation

    def scalar_one_or_none(self) -> SimpleNamespace | None:
        return self._reconciliation

    def scalars(self):
        return self

    def all(self) -> list[SimpleNamespace]:
        return [] if self._reconciliation is None else [self._reconciliation]


class _LedgerSession:
    def __init__(
        self,
        identities: list[SimpleNamespace],
        *,
        present: bool,
        state: str,
        numeric_user_id: int,
        legacy_uuid: str | None,
    ) -> None:
        self._identities = identities
        self._present = present
        self._state = state
        self._numeric_user_id = numeric_user_id
        self._legacy_uuid = legacy_uuid
        self.execute_calls = 0

    async def execute(self, _statement) -> _LedgerResult:
        self.execute_calls += 1
        if len(self._identities) != 1:
            raise AssertionError("ambiguous raw candidates must fail before ledger resolution")
        if not self._present:
            return _LedgerResult(None)
        identity = self._identities[0]
        return _LedgerResult(
            SimpleNamespace(
                subject_type="service_identity",
                subject_id=identity.id,
                numeric_user_id=self._numeric_user_id,
                legacy_uuid=self._legacy_uuid,
                reconciliation_state=self._state,
            )
        )


@pytest.fixture(autouse=True)
def _configure_gateway_external_squads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", SMART_RU_EXTERNAL_SQUAD_UUID)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_external_squad_uuid", TASK2_EXTERNAL_SQUAD_UUID)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "premium_spb_de_exceptions")


def _identity(plan_code: str) -> SimpleNamespace:
    customer_id = uuid4()
    realm_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        customer_account_id=customer_id,
        auth_realm_id=realm_id,
        provider_numeric_subject_id=PROVIDER_NUMERIC_SUBJECT_ID,
        provider_subject_ref=PROVIDER_SUBJECT_REF,
        service_context={"plan_code": plan_code},
    )


def _grant(identity: SimpleNamespace, *, plan_code: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        customer_account_id=identity.customer_account_id,
        auth_realm_id=identity.auth_realm_id,
        grant_snapshot={"plan_code": plan_code or identity.service_context["plan_code"]},
    )


def _grant_with_snapshot(identity: SimpleNamespace, grant_snapshot: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        customer_account_id=identity.customer_account_id,
        auth_realm_id=identity.auth_realm_id,
        grant_snapshot=grant_snapshot,
    )


def _use_case(
    identities: list[SimpleNamespace],
    grants: dict[object, SimpleNamespace | None],
    *,
    external_squad_uuid: str | None = None,
    provider_uuid: str | None = PROVIDER_SUBJECT_REF,
    ledger_present: bool = True,
    ledger_state: str = "mapped",
    ledger_numeric_user_id: int = PROVIDER_NUMERIC_SUBJECT_ID,
    ledger_legacy_uuid: str | None = PROVIDER_SUBJECT_REF,
):
    client = _RemnawaveClient(
        {
            "id": PROVIDER_NUMERIC_SUBJECT_ID,
            "uuid": provider_uuid,
            "status": "ACTIVE",
            "externalSquadUuid": external_squad_uuid,
        }
    )
    ledger_session = _LedgerSession(
        identities,
        present=ledger_present,
        state=ledger_state,
        numeric_user_id=ledger_numeric_user_id,
        legacy_uuid=ledger_legacy_uuid,
    )
    use_case = ResolveSubscriptionProductUseCase(
        cast(AsyncSession, ledger_session),
        cast(RemnawaveClient, client),
    )
    use_case._repo = cast(ServiceAccessRepository, _Repository(identities, grants))
    return use_case, client


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_code", ["premium_smart_ru", "premium_spb_de_exceptions"])
async def test_resolves_one_active_supported_product(plan_code: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if plan_code == "premium_spb_de_exceptions":
        enable_spb_de_readiness(monkeypatch)
    identity = _identity(plan_code)
    use_case, client = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=EXPECTED_EXTERNAL_SQUAD_UUIDS[plan_code],
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == plan_code
    assert result.xray_failover_canary is False
    assert client.paths == ["/users/by-short-uuid/abcdefghijklmnop"]


@pytest.mark.asyncio
async def test_task2_grant_fails_closed_when_data_plane_is_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_spb_de_exceptions")
    use_case, client = _use_case([identity], {identity.id: _grant(identity)})

    for _ in range(2):
        with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
            await use_case.execute("abcdefghijklmnop")
        assert exc_info.value.reason == "spb_de_exceptions_data_plane_not_ready"

    assert client.paths == ["/users/by-short-uuid/abcdefghijklmnop", "/users/by-short-uuid/abcdefghijklmnop"]


@pytest.mark.asyncio
async def test_task2_identity_with_sparse_active_grant_fails_closed_when_data_plane_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case([identity], {identity.id: _grant_with_snapshot(identity, {})})

    with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
        await use_case.execute("abcdefghijklmnop")

    assert exc_info.value.reason == "spb_de_exceptions_data_plane_not_ready"


@pytest.mark.asyncio
async def test_task2_identity_with_sparse_active_grant_resolves_when_data_plane_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    identity = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant_with_snapshot(identity, {})},
        external_squad_uuid=TASK2_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_spb_de_exceptions"


@pytest.mark.asyncio
async def test_smart_ru_resolves_when_task2_data_plane_is_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=SMART_RU_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_smart_ru"


@pytest.mark.asyncio
async def test_smart_ru_xray_failover_canary_resolves_only_from_service_context_json_true() -> None:
    identity = _identity("premium_smart_ru")
    identity.service_context[PREMIUM_SMART_RU_XRAY_FAILOVER_CANARY_CONTEXT_KEY] = True
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=SMART_RU_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_smart_ru"
    assert result.xray_failover_canary is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stored_value",
    [False, "true", "1", 1, "yes", None],
)
async def test_smart_ru_xray_failover_canary_rejects_non_json_true_values(stored_value: object) -> None:
    identity = _identity("premium_smart_ru")
    identity.service_context[PREMIUM_SMART_RU_XRAY_FAILOVER_CANARY_CONTEXT_KEY] = stored_value
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=SMART_RU_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_smart_ru"
    assert result.xray_failover_canary is False


@pytest.mark.asyncio
async def test_xray_failover_canary_marker_is_ignored_for_non_smart_ru_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    identity = _identity("premium_spb_de_exceptions")
    identity.service_context[PREMIUM_SMART_RU_XRAY_FAILOVER_CANARY_CONTEXT_KEY] = True
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=TASK2_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_spb_de_exceptions"
    assert result.xray_failover_canary is False


@pytest.mark.asyncio
async def test_smart_ru_resolves_when_task2_plan_codes_overlap_and_data_plane_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", OVERLAPPING_PLAN_CODES)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=SMART_RU_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_smart_ru"


@pytest.mark.asyncio
async def test_task2_readiness_false_does_not_expose_provider_only_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    use_case, _ = _use_case([], {})

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
async def test_rejects_invalid_short_uuid_before_provider_lookup() -> None:
    use_case, client = _use_case([], {})

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("../not-a-token")

    assert client.paths == []


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_numeric_id", [None, 0, -1, True, "4201"])
async def test_provider_response_requires_exact_positive_numeric_identity(invalid_numeric_id) -> None:
    use_case, client = _use_case([], {})
    client.payload["id"] = invalid_numeric_id

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")

    assert client.paths == ["/users/by-short-uuid/abcdefghijklmnop"]


@pytest.mark.asyncio
async def test_rejects_identity_without_active_entitlement() -> None:
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case([identity], {identity.id: None})

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ledger_present", "ledger_state", "ledger_numeric_user_id", "ledger_legacy_uuid"),
    [
        (False, "mapped", PROVIDER_NUMERIC_SUBJECT_ID, PROVIDER_SUBJECT_REF),
        (True, "pending", PROVIDER_NUMERIC_SUBJECT_ID, PROVIDER_SUBJECT_REF),
        (True, "conflict", PROVIDER_NUMERIC_SUBJECT_ID, PROVIDER_SUBJECT_REF),
        (True, "mapped", 9999, PROVIDER_SUBJECT_REF),
        (True, "mapped", PROVIDER_NUMERIC_SUBJECT_ID, "f165a822-c652-48c4-a29b-fb93962c155c"),
    ],
)
async def test_fails_unavailable_before_grant_lookup_without_one_exact_mapped_ledger_row(
    ledger_present: bool,
    ledger_state: str,
    ledger_numeric_user_id: int,
    ledger_legacy_uuid: str,
) -> None:
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        ledger_present=ledger_present,
        ledger_state=ledger_state,
        ledger_numeric_user_id=ledger_numeric_user_id,
        ledger_legacy_uuid=ledger_legacy_uuid,
    )

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")

    assert cast(_Repository, use_case._repo).grant_checks == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_uuid",
    ["f165a822-c652-48c4-a29b-fb93962c155c", "not-a-uuid"],
)
async def test_fails_unavailable_when_provider_legacy_uuid_is_not_the_exact_local_reference(
    provider_uuid: str,
) -> None:
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        provider_uuid=provider_uuid,
    )

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")

    assert cast(_Repository, use_case._repo).grant_checks == []


@pytest.mark.asyncio
async def test_accepts_exact_numeric_mapping_when_provider_omits_legacy_uuid() -> None:
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        provider_uuid=None,
        external_squad_uuid=SMART_RU_EXTERNAL_SQUAD_UUID,
    )

    result = await use_case.execute("abcdefghijklmnop")

    assert result.product_code == "premium_smart_ru"


@pytest.mark.asyncio
async def test_fails_closed_when_provider_subject_maps_to_two_products() -> None:
    smart = _identity("premium_smart_ru")
    spb = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case(
        [smart, spb],
        {smart.id: _grant(smart), spb.id: _grant(spb)},
    )

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")

    assert cast(_LedgerSession, use_case._session).execute_calls == 0
    assert cast(_Repository, use_case._repo).grant_checks == []


@pytest.mark.asyncio
async def test_fails_closed_when_supported_product_shares_subject_with_unsupported_active_grant() -> None:
    smart = _identity("premium_smart_ru")
    unsupported = _identity("unrelated_plan")
    use_case, _ = _use_case(
        [smart, unsupported],
        {smart.id: _grant(smart), unsupported.id: _grant(unsupported)},
    )

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")

    assert cast(_LedgerSession, use_case._session).execute_calls == 0
    assert cast(_Repository, use_case._repo).grant_checks == []


@pytest.mark.asyncio
async def test_fails_closed_when_active_grant_realm_does_not_match_identity() -> None:
    identity = _identity("premium_smart_ru")
    mismatched_grant = _grant(identity)
    mismatched_grant.auth_realm_id = uuid4()
    use_case, _ = _use_case([identity], {identity.id: mismatched_grant})

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
async def test_fails_closed_when_identity_plan_disagrees_with_active_grant_snapshot() -> None:
    identity = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case([identity], {identity.id: _grant(identity, plan_code="premium_smart_ru")})

    with pytest.raises(SubscriptionGatewayUnavailableError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
@pytest.mark.parametrize("conflict_source", ["grant_snapshot", "service_context"])
async def test_fails_closed_when_single_snapshot_has_conflicting_product_fields(conflict_source: str) -> None:
    identity = _identity("premium_smart_ru")
    grant = _grant(identity, plan_code="premium_smart_ru")
    if conflict_source == "grant_snapshot":
        grant.grant_snapshot = {
            "plan_code": "premium_smart_ru",
            "remnawave_routing_product": "premium_spb_de_exceptions",
        }
    else:
        identity.service_context = {
            "plan_code": "premium_smart_ru",
            "remnawave_routing_product": "premium_spb_de_exceptions",
        }
    use_case, _ = _use_case([identity], {identity.id: grant})

    with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
        await use_case.execute("abcdefghijklmnop")

    assert exc_info.value.reason == PRODUCT_PLAN_MISMATCH_REASON


@pytest.mark.asyncio
async def test_smart_ru_fails_closed_when_provider_external_squad_mismatches_product() -> None:
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=TASK2_EXTERNAL_SQUAD_UUID,
    )

    with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
        await use_case.execute("abcdefghijklmnop")

    assert exc_info.value.reason == EXTERNAL_SQUAD_MISMATCH_REASON


@pytest.mark.asyncio
async def test_task2_fails_closed_when_provider_external_squad_mismatches_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    identity = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case(
        [identity],
        {identity.id: _grant(identity)},
        external_squad_uuid=SMART_RU_EXTERNAL_SQUAD_UUID,
    )

    with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
        await use_case.execute("abcdefghijklmnop")

    assert exc_info.value.reason == EXTERNAL_SQUAD_MISMATCH_REASON


@pytest.mark.asyncio
async def test_task2_malformed_public_key_fails_closed_as_gateway_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = make_spb_de_readiness_attestation()
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", artifact.token)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", "not-a-public-key")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", "")
    identity = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case([identity], {identity.id: _grant(identity)})

    with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
        await use_case.execute("abcdefghijklmnop")

    assert exc_info.value.reason == TASK2_READINESS_SIGNATURE_INVALID_REASON


@pytest.mark.asyncio
async def test_task2_stale_manifest_attestation_fails_closed_as_gateway_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    stale_pointer = manifest_pointer_json(manifest_sha256="c" * 64)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", stale_pointer)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", stale_pointer)
    identity = _identity("premium_spb_de_exceptions")
    use_case, _ = _use_case([identity], {identity.id: _grant(identity)})

    with pytest.raises(SubscriptionGatewayUnavailableError) as exc_info:
        await use_case.execute("abcdefghijklmnop")

    assert exc_info.value.reason == TASK2_READINESS_MANIFEST_MISMATCH_REASON


@pytest.mark.asyncio
async def test_rejects_unsupported_plan_even_with_active_grant() -> None:
    identity = _identity("unrelated_plan")
    use_case, _ = _use_case([identity], {identity.id: _grant(identity)})

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
async def test_rejects_stale_provider_active_smart_ru_squad_without_backend_identity() -> None:
    squad_uuid = "409147a7-a03c-4db5-bccf-33d3caaf8d52"
    use_case, _ = _use_case([], {}, external_squad_uuid=squad_uuid)

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
async def test_does_not_use_legacy_squad_to_bypass_inactive_backend_grant() -> None:
    squad_uuid = "409147a7-a03c-4db5-bccf-33d3caaf8d52"
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case([identity], {identity.id: None}, external_squad_uuid=squad_uuid)

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")


@pytest.mark.asyncio
async def test_rejects_any_legacy_external_squad_without_backend_identity() -> None:
    use_case, _ = _use_case(
        [],
        {},
        external_squad_uuid="ed139a4b-d21f-478a-b1d2-73ce9d9012ea",
    )

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")
