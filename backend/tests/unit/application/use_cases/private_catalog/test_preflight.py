from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest

from src.application.use_cases.growth_codes.namespace import NormalizedCustomerCode, normalize_customer_input_code
from src.application.use_cases.private_catalog.preflight import (
    PrivateCatalogCodeInput,
    PrivateCatalogGrantRecord,
    PrivateCatalogPreflightCommand,
    PrivateCatalogPreflightUseCase,
    PrivateCatalogRiskBlockedError,
    PrivatePlanPreview,
    PrivatePolicyRecord,
    PrivateStorefrontRecord,
    build_private_code_set_hash,
    build_private_code_set_id,
)

POLICY_ID = UUID("10000000-0000-0000-0000-000000000001")
POLICY_VERSION_ID = UUID("10000000-0000-0000-0000-000000000002")
GROWTH_CODE_ID = UUID("10000000-0000-0000-0000-000000000003")
PLAN_ID = UUID("10000000-0000-0000-0000-000000000004")
STOREFRONT_ID = UUID("10000000-0000-0000-0000-000000000005")
REALM_ID = UUID("10000000-0000-0000-0000-000000000006")
GRANT_ID = UUID("10000000-0000-0000-0000-000000000007")
USER_ID = UUID("10000000-0000-0000-0000-000000000008")


class FakePrivateCatalogRepository:
    def __init__(self) -> None:
        self.storefront = PrivateStorefrontRecord(
            id=STOREFRONT_ID,
            auth_realm_id=REALM_ID,
            storefront_key="ru",
        )
        self.policies_by_hash: dict[str, PrivatePolicyRecord] = {}
        self.plan_previews: tuple[PrivatePlanPreview, ...] = ()
        self.storefront_calls = 0
        self.policy_calls: list[str] = []
        self.created_grants: list[dict[str, object]] = []

    async def get_storefront(self, storefront_key: str) -> PrivateStorefrontRecord | None:
        self.storefront_calls += 1
        if storefront_key != self.storefront.storefront_key:
            return None
        return self.storefront

    async def find_active_private_policy(self, code_hash: str) -> PrivatePolicyRecord | None:
        self.policy_calls.append(code_hash)
        return self.policies_by_hash.get(code_hash)

    async def list_private_plan_previews(
        self,
        *,
        plan_ids: tuple[UUID, ...],
        channel: str,
        currency: str,
    ) -> tuple[PrivatePlanPreview, ...]:
        assert plan_ids == (PLAN_ID,)
        assert channel == "web"
        assert currency == "RUB"
        return self.plan_previews

    async def create_private_catalog_grant(
        self,
        *,
        policy: PrivatePolicyRecord,
        storefront: PrivateStorefrontRecord,
        normalized_codes: tuple[NormalizedCustomerCode, ...],
        code_set_hash: str,
        channel: str,
        user_id: UUID | None,
        anonymous_session_id: str | None,
        issued_at: datetime,
        expires_at: datetime,
    ) -> PrivateCatalogGrantRecord:
        assert policy.id == POLICY_ID
        assert storefront.id == STOREFRONT_ID
        assert issued_at.tzinfo is not None
        assert expires_at > issued_at
        self.created_grants.append(
            {
                "code_set_hash": code_set_hash,
                "channel": channel,
                "user_id": user_id,
                "anonymous_session_id": anonymous_session_id,
                "prefixes": tuple(code.code_prefix for code in normalized_codes),
            }
        )
        return PrivateCatalogGrantRecord(id=GRANT_ID, expires_at=expires_at)


class FakePrivateCatalogRiskGuard:
    def __init__(self, *, block: bool = False) -> None:
        self.block = block
        self.calls: list[dict[str, object]] = []

    async def evaluate_private_preflight(
        self,
        *,
        user_id: UUID | None,
        anonymous_session_id: str | None,
        storefront: PrivateStorefrontRecord,
        policy: PrivatePolicyRecord,
        code_set_id: UUID,
        code_set_hash: str,
        channel: str,
        currency: str,
        code_count: int,
    ) -> str:
        self.calls.append(
            {
                "user_id": user_id,
                "anonymous_session_id": anonymous_session_id,
                "storefront_id": storefront.id,
                "policy_id": policy.id,
                "code_set_id": code_set_id,
                "code_set_hash": code_set_hash,
                "channel": channel,
                "currency": currency,
                "code_count": code_count,
            }
        )
        if self.block:
            raise PrivateCatalogRiskBlockedError("review")
        return "allow"


def _policy_for(raw_code: str, *, requires_auth: bool = False) -> tuple[str, PrivatePolicyRecord]:
    normalized = normalize_customer_input_code(raw_code)
    return normalized.code_hash, PrivatePolicyRecord(
        id=POLICY_ID,
        policy_version_id=POLICY_VERSION_ID,
        growth_code_id=GROWTH_CODE_ID,
        target_plan_ids=(PLAN_ID,),
        allowed_storefront_ids=(STOREFRONT_ID,),
        allowed_channels=("web",),
        grant_ttl_seconds=900,
        max_quote_conversions=1,
        requires_auth=requires_auth,
    )


def _plan_preview() -> PrivatePlanPreview:
    return PrivatePlanPreview(
        plan_id=PLAN_ID,
        display_name="RU Basic 90",
        plan_code="ru_basic_90",
        duration_days=90,
        amount=Decimal("990.00"),
        currency="RUB",
        entitlement_summary={"devices_included": 3, "support_sla": "standard"},
    )


@pytest.mark.asyncio
async def test_private_catalog_preflight_issues_scoped_grant_and_offer_without_raw_code() -> None:
    repo = FakePrivateCatalogRepository()
    raw_code = "PR-RU90-ACCESS"
    code_hash, policy = _policy_for(raw_code)
    repo.policies_by_hash[code_hash] = policy
    repo.plan_previews = (_plan_preview(),)

    result = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="WEB",
            currency="rub",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert result.status == "accepted"
    assert result.code_set_id == build_private_code_set_id(result.code_set_hash)
    assert result.applications[0].status == "accepted"
    assert result.applications[0].roles == ("catalog_access",)
    assert result.applications[0].message_key == "growth.code.privateOfferUnlocked"
    assert result.private_catalog_grant is not None
    assert result.private_catalog_grant.id == GRANT_ID
    assert len(result.private_offers) == 1
    assert result.private_offers[0].plan_id == PLAN_ID
    assert result.private_offers[0].price_amount == "990.00"
    assert result.private_offers[0].private_catalog_grant_id == GRANT_ID
    assert repo.created_grants[0]["anonymous_session_id"] == "anon-checkout-1"
    assert repo.created_grants[0]["user_id"] is None
    assert raw_code not in str(repo.created_grants[0])


@pytest.mark.asyncio
async def test_private_catalog_preflight_records_allowing_risk_guard_before_grant() -> None:
    repo = FakePrivateCatalogRepository()
    risk_guard = FakePrivateCatalogRiskGuard()
    raw_code = "PR-RU90-ACCESS"
    code_hash, policy = _policy_for(raw_code)
    repo.policies_by_hash[code_hash] = policy
    repo.plan_previews = (_plan_preview(),)

    result = await PrivateCatalogPreflightUseCase(repo, risk_guard=risk_guard).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="web",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert result.status == "accepted"
    assert result.private_catalog_grant is not None
    assert result.risk.action == "allow"
    assert len(risk_guard.calls) == 1
    assert risk_guard.calls[0]["policy_id"] == POLICY_ID
    assert risk_guard.calls[0]["code_set_id"] == result.code_set_id
    assert repo.created_grants


@pytest.mark.asyncio
async def test_private_catalog_preflight_blocks_grant_when_risk_guard_requires_review() -> None:
    repo = FakePrivateCatalogRepository()
    risk_guard = FakePrivateCatalogRiskGuard(block=True)
    raw_code = "PR-RU90-ACCESS"
    code_hash, policy = _policy_for(raw_code)
    repo.policies_by_hash[code_hash] = policy
    repo.plan_previews = (_plan_preview(),)

    result = await PrivateCatalogPreflightUseCase(repo, risk_guard=risk_guard).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="web",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert result.status == "denied_by_risk"
    assert result.private_catalog_grant is None
    assert result.private_offers == ()
    assert result.risk.action == "review"
    assert result.applications[0].status == "rejected"
    assert result.applications[0].message_key == "growth.risk.verificationRequired"
    assert len(risk_guard.calls) == 1
    assert repo.created_grants == []


@pytest.mark.asyncio
async def test_private_catalog_preflight_rejects_invalid_code_without_private_leak() -> None:
    repo = FakePrivateCatalogRepository()

    result = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code="PR-RU90-UNKNOWN", client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="web",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert result.status == "rejected"
    assert result.private_catalog_grant is None
    assert result.private_offers == ()
    assert repo.created_grants == []
    assert result.applications[0].status == "rejected"
    assert result.applications[0].message_key == "growth.code.notEligible"
    assert result.applications[0].masked_code != "PR-RU90-UNKNOWN"


@pytest.mark.asyncio
async def test_private_catalog_preflight_requires_subject_before_policy_lookup() -> None:
    repo = FakePrivateCatalogRepository()

    result = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code="PR-RU90-ACCESS", client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="web",
            currency="RUB",
        )
    )

    assert result.status == "rejected"
    assert repo.storefront_calls == 0
    assert repo.policy_calls == []
    assert repo.created_grants == []


@pytest.mark.asyncio
async def test_private_catalog_preflight_rejects_auth_required_policy_for_anonymous_subject() -> None:
    repo = FakePrivateCatalogRepository()
    raw_code = "PR-RU90-ACCESS"
    code_hash, policy = _policy_for(raw_code, requires_auth=True)
    repo.policies_by_hash[code_hash] = policy
    repo.plan_previews = (_plan_preview(),)

    result = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="web",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert result.status == "rejected"
    assert result.private_catalog_grant is None
    assert result.private_offers == ()
    assert repo.created_grants == []


@pytest.mark.asyncio
async def test_private_catalog_preflight_allows_auth_required_policy_for_user_subject() -> None:
    repo = FakePrivateCatalogRepository()
    raw_code = "PR-RU90-ACCESS"
    code_hash, policy = _policy_for(raw_code, requires_auth=True)
    repo.policies_by_hash[code_hash] = policy
    repo.plan_previews = (_plan_preview(),)

    result = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="web",
            currency="RUB",
            user_id=USER_ID,
        )
    )

    assert result.status == "accepted"
    assert repo.created_grants[0]["user_id"] == USER_ID
    assert repo.created_grants[0]["anonymous_session_id"] is None


@pytest.mark.asyncio
async def test_private_catalog_preflight_rejects_wrong_storefront_or_channel() -> None:
    repo = FakePrivateCatalogRepository()
    raw_code = "PR-RU90-ACCESS"
    code_hash, policy = _policy_for(raw_code)
    repo.policies_by_hash[code_hash] = policy
    repo.plan_previews = (_plan_preview(),)

    wrong_storefront = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="global",
            channel="web",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )
    wrong_channel = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(PrivateCatalogCodeInput(code=raw_code, client_slot_id="slot-private"),),
            storefront_key="ru",
            channel="partner",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert wrong_storefront.status == "rejected"
    assert wrong_channel.status == "rejected"
    assert repo.created_grants == []


def test_private_code_set_hash_is_permutation_independent() -> None:
    first = normalize_customer_input_code("PR-RU90-ACCESS")
    second = normalize_customer_input_code("PR-PRO100-INV10")

    first_hash = build_private_code_set_hash(
        normalized_codes=(first, second),
        storefront_key="ru",
        channel="web",
    )
    second_hash = build_private_code_set_hash(
        normalized_codes=(second, first),
        storefront_key="ru",
        channel="web",
    )

    assert first_hash == second_hash
    assert build_private_code_set_id(first_hash) == build_private_code_set_id(second_hash)
    assert build_private_code_set_id(first_hash).version == 5


@pytest.mark.asyncio
async def test_private_catalog_preflight_rejects_duplicate_codes_without_policy_lookup() -> None:
    repo = FakePrivateCatalogRepository()

    result = await PrivateCatalogPreflightUseCase(repo).execute(
        PrivateCatalogPreflightCommand(
            codes=(
                PrivateCatalogCodeInput(code="PR-RU90-ACCESS", client_slot_id="slot-a"),
                PrivateCatalogCodeInput(code=" pr-ru90-access ", client_slot_id="slot-b"),
            ),
            storefront_key="ru",
            channel="web",
            currency="RUB",
            anonymous_session_id="anon-checkout-1",
        )
    )

    assert result.status == "rejected"
    assert [item.message_key for item in result.applications] == [
        "growth.errors.duplicateCode",
        "growth.errors.duplicateCode",
    ]
    assert result.private_catalog_grant is None
    assert repo.storefront_calls == 0
    assert repo.policy_calls == []
    assert repo.created_grants == []
