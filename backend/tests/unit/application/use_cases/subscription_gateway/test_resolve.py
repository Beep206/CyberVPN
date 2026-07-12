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

    async def list_active_subscription_identities_by_provider_subject(self, **kwargs):
        assert kwargs == {
            "provider_name": "remnawave",
            "provider_subject_ref": "e131349d-1d45-4a21-ac66-4e98fa54c22d",
        }
        return self.identities

    async def get_active_entitlement_grant_for_service_identity(self, *, service_identity_id, now):
        assert now.tzinfo is not None
        self.grant_checks.append(service_identity_id)
        return self.grants.get(service_identity_id)


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
):
    client = _RemnawaveClient(
        {
            "uuid": "e131349d-1d45-4a21-ac66-4e98fa54c22d",
            "status": "ACTIVE",
            "externalSquadUuid": external_squad_uuid,
        }
    )
    use_case = ResolveSubscriptionProductUseCase(
        cast(AsyncSession, SimpleNamespace()),
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
async def test_rejects_identity_without_active_entitlement() -> None:
    identity = _identity("premium_smart_ru")
    use_case, _ = _use_case([identity], {identity.id: None})

    with pytest.raises(SubscriptionGatewayNotFoundError):
        await use_case.execute("abcdefghijklmnop")


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

    assert cast(_Repository, use_case._repo).grant_checks == [smart.id, unsupported.id]


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
