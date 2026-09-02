"""Fail-closed settlement for ambiguous customer Remnawave creates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptService,
    RemnawaveMutationAttemptService,
)
from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    _acquire_remnawave_identity_registry_lock,
    persist_runtime_mapped_mobile_identity,
    resolve_exact_mapped_mobile_user_ref,
)
from src.domain.entities.user import User
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel

CUSTOMER_CREATE_ATTEMPT_SCOPE = "remnawave-customer:create"
CUSTOMER_CREATE_RESOURCE_TYPE = "remnawave_user_create"

_SETTLEABLE_STATES = frozenset({"reconciliation_required"})
_TERMINAL_CUSTOMER_STATES = frozenset({"deleting", "deleted"})
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EMAIL_PLACEHOLDER_SUFFIXES = (".local", ".localhost")


class RemnawaveCustomerCreateAttemptNotFound(RuntimeError):
    """The requested UUID is not a customer-create attempt visible here."""


class RemnawaveCustomerCreateAttemptConflict(RuntimeError):
    """The requested state transition or identity binding is unsafe."""


class RemnawaveCustomerUserLookup(Protocol):
    async def get_by_ref(self, ref: RemnawaveUserRef) -> User | None: ...


@dataclass(frozen=True, slots=True)
class RemnawaveCustomerCreateAttemptResult:
    attempt_id: UUID
    customer_account_id: UUID
    state: Literal["completed", "reconciliation_required"]
    changed: bool
    user_ref: RemnawaveUserRef | None = None


def canonical_customer_provider_usernames(customer_account_id: UUID) -> frozenset[str]:
    """Return every exact customer-create username emitted by current flows."""

    return frozenset(
        {
            f"cvpn_t_{customer_account_id.hex[:28]}",
            f"cvpn_p_{customer_account_id.hex[:28]}",
            f"cvpn_m_{customer_account_id.hex[:28]}",
            f"cvpn_g_{customer_account_id.hex[:28]}",
            f"cvpn_ts_{customer_account_id.hex[:27]}",
        }
    )


def _canonical_provider_email(customer_email: str, *, provider_username: str) -> str:
    """Mirror the existing Remnawave boundary's placeholder-email contract."""

    normalized = customer_email.strip().lower()
    domain = normalized.rsplit("@", 1)[-1] if "@" in normalized else ""
    if _EMAIL_RE.fullmatch(normalized) and not domain.endswith(_EMAIL_PLACEHOLDER_SUFFIXES):
        return normalized
    return f"{provider_username}@cyber-vpn.net"


def _same_ref(left: RemnawaveUserRef, right: RemnawaveUserRef) -> bool:
    return left.require_numeric_id() == right.require_numeric_id() and left.legacy_uuid == right.legacy_uuid


class RemnawaveCustomerCreateAttemptSettlementService:
    """Settle/reopen one exact durable customer-create marker.

    The attempt and customer rows are locked in this order. Provider readback
    is mandatory for an open attempt, and the resulting mapping, attempt
    completion, and caller-owned audit write share one database transaction.
    No path in this service issues a provider mutation.
    """

    def __init__(self, session: AsyncSession, provider_users: RemnawaveCustomerUserLookup | None) -> None:
        self._session = session
        self._provider_users = provider_users

    async def settle(
        self,
        *,
        attempt_id: UUID,
        provider_numeric_user_id: int,
        provider_legacy_uuid: UUID | None,
    ) -> RemnawaveCustomerCreateAttemptResult:
        # Retirement takes the exclusive registry lock before attempt rows.
        # Preserve that global order so settlement cannot deadlock with it.
        await _acquire_remnawave_identity_registry_lock(self._session, shared=True)
        attempt = await self._load_scoped_attempt_for_update(attempt_id)
        customer_account_id = self._customer_account_id(attempt)
        customer = await self._load_customer_for_update(customer_account_id)

        requested_ref = RemnawaveUserRef(id=provider_numeric_user_id, legacy_uuid=provider_legacy_uuid)
        if attempt.status == "completed":
            return await self._completed_replay_result(
                attempt=attempt,
                customer=customer,
                requested_ref=requested_ref,
            )
        if attempt.status not in _SETTLEABLE_STATES:
            raise RemnawaveCustomerCreateAttemptConflict("Only reconciliation-required customer creates can be settled")
        self._assert_customer_active(customer)

        if self._provider_users is None:  # pragma: no cover - constructor misuse guard
            raise RuntimeError("Settlement requires an authoritative Remnawave user lookup")
        provider_user = await self._provider_users.get_by_ref(requested_ref)
        if provider_user is None:
            raise RemnawaveCustomerCreateAttemptConflict("Provider user was not found by the exact numeric identity")
        provider_ref = self._verify_provider_identity(
            customer=customer,
            requested_ref=requested_ref,
            provider_user=provider_user,
        )

        try:
            mapped_ref = await persist_runtime_mapped_mobile_identity(
                self._session,
                customer=customer,
                remnawave_user_id=provider_ref.require_numeric_id(),
                remnawave_uuid=provider_ref.legacy_uuid,
                source="admin_customer_create_settlement",
            )
        except RemnawaveIdentityAccessConflict as exc:
            raise RemnawaveCustomerCreateAttemptConflict(
                "Provider identity conflicts with the canonical customer mapping"
            ) from exc

        await RemnawaveCreateAttemptService(self._session).mark_completed(attempt, user_ref=mapped_ref)
        return RemnawaveCustomerCreateAttemptResult(
            attempt_id=attempt.id,
            customer_account_id=customer_account_id,
            state="completed",
            changed=True,
            user_ref=mapped_ref,
        )

    async def reopen(self, *, attempt_id: UUID) -> RemnawaveCustomerCreateAttemptResult:
        await _acquire_remnawave_identity_registry_lock(self._session, shared=True)
        attempt = await self._load_scoped_attempt_for_update(attempt_id)
        customer_account_id = self._customer_account_id(attempt)
        customer = await self._load_customer_for_update(customer_account_id)
        self._assert_customer_active(customer)
        if attempt.status != "rejected":
            raise RemnawaveCustomerCreateAttemptConflict(
                "Only a rejected customer create can be reopened for reconciliation"
            )

        # Reopening never re-arms the mutation. Existing-attempt evaluation
        # treats reconciliation_required as should_mutate=False.
        attempt.status = "reconciliation_required"
        attempt.response_payload = {}
        await self._session.flush()
        return RemnawaveCustomerCreateAttemptResult(
            attempt_id=attempt.id,
            customer_account_id=customer_account_id,
            state="reconciliation_required",
            changed=True,
        )

    async def _load_scoped_attempt_for_update(self, attempt_id: UUID) -> ApiIdempotencyRecordModel:
        result = await self._session.execute(
            select(ApiIdempotencyRecordModel)
            .where(
                ApiIdempotencyRecordModel.id == attempt_id,
                ApiIdempotencyRecordModel.scope == CUSTOMER_CREATE_ATTEMPT_SCOPE,
                ApiIdempotencyRecordModel.resource_type == CUSTOMER_CREATE_RESOURCE_TYPE,
                ApiIdempotencyRecordModel.resource_id.is_not(None),
            )
            .with_for_update()
        )
        attempt = result.scalars().one_or_none()
        if attempt is None:
            raise RemnawaveCustomerCreateAttemptNotFound("Customer create attempt not found")
        return attempt

    async def _load_customer_for_update(self, customer_account_id: UUID) -> MobileUserModel:
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.id == customer_account_id).with_for_update()
        )
        customer = result.scalars().one_or_none()
        if customer is None:
            raise RemnawaveCustomerCreateAttemptNotFound("Customer create attempt not found")
        return customer

    async def _completed_replay_result(
        self,
        *,
        attempt: ApiIdempotencyRecordModel,
        customer: MobileUserModel,
        requested_ref: RemnawaveUserRef,
    ) -> RemnawaveCustomerCreateAttemptResult:
        completed_ref = RemnawaveMutationAttemptService.completed_ref(attempt)
        if completed_ref is None or completed_ref.require_numeric_id() != requested_ref.require_numeric_id():
            raise RemnawaveCustomerCreateAttemptConflict("Completed attempt has a different provider identity")
        if requested_ref.legacy_uuid is not None and completed_ref.legacy_uuid != requested_ref.legacy_uuid:
            raise RemnawaveCustomerCreateAttemptConflict("Completed attempt has a different rollback reference")

        try:
            mapped_ref = await resolve_exact_mapped_mobile_user_ref(self._session, customer)
        except RemnawaveIdentityAccessConflict as exc:
            raise RemnawaveCustomerCreateAttemptConflict(
                "Completed attempt no longer has an exact canonical customer mapping"
            ) from exc
        if mapped_ref is None or not _same_ref(mapped_ref, completed_ref):
            raise RemnawaveCustomerCreateAttemptConflict(
                "Completed attempt no longer has an exact canonical customer mapping"
            )
        return RemnawaveCustomerCreateAttemptResult(
            attempt_id=attempt.id,
            customer_account_id=customer.id,
            state="completed",
            changed=False,
            user_ref=mapped_ref,
        )

    @staticmethod
    def _customer_account_id(attempt: ApiIdempotencyRecordModel) -> UUID:
        customer_account_id = attempt.resource_id
        if not isinstance(customer_account_id, UUID):
            raise RemnawaveCustomerCreateAttemptNotFound("Customer create attempt not found")
        return customer_account_id

    @staticmethod
    def _assert_customer_active(customer: MobileUserModel) -> None:
        if customer.status in _TERMINAL_CUSTOMER_STATES:
            raise RemnawaveCustomerCreateAttemptConflict("Customer account no longer accepts identity settlement")

    @staticmethod
    def _verify_provider_identity(
        *,
        customer: MobileUserModel,
        requested_ref: RemnawaveUserRef,
        provider_user: User,
    ) -> RemnawaveUserRef:
        if provider_user.remnawave_id != requested_ref.require_numeric_id():
            raise RemnawaveCustomerCreateAttemptConflict("Provider numeric identity readback does not match")
        if requested_ref.legacy_uuid is not None and provider_user.uuid != requested_ref.legacy_uuid:
            raise RemnawaveCustomerCreateAttemptConflict("Provider rollback reference readback does not match")
        if provider_user.username not in canonical_customer_provider_usernames(customer.id):
            raise RemnawaveCustomerCreateAttemptConflict("Provider username is not canonical for this customer")
        expected_email = _canonical_provider_email(customer.email, provider_username=provider_user.username)
        if provider_user.email is None or provider_user.email.strip().lower() != expected_email:
            raise RemnawaveCustomerCreateAttemptConflict("Provider email is not canonical for this customer")
        return RemnawaveUserRef(id=provider_user.remnawave_id, legacy_uuid=provider_user.uuid)
