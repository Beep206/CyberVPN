"""Privacy request domain states and safe transition rules."""

from __future__ import annotations

from enum import StrEnum


class PrivacyRequestError(Exception):
    """Base privacy request error."""


class PrivacyRequestNotFoundError(PrivacyRequestError):
    """Raised when a privacy request is absent or outside caller scope."""


class InvalidPrivacyRequestTransitionError(PrivacyRequestError):
    """Raised when a status transition violates the privacy workflow."""


class PrivacyRequestType(StrEnum):
    ACCOUNT_DELETION = "account_deletion"
    DATA_EXPORT = "data_export"


class PrivacyRequestStatus(StrEnum):
    SUBMITTED = "submitted"
    IDENTITY_VERIFICATION = "identity_verification"
    PENDING_DECISION = "pending_decision"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    FULFILLED = "fulfilled"
    DENIED = "denied"
    CANCELED = "canceled"
    FAILED = "failed"


class PrivacyRequestActorType(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    SYSTEM = "system"


ACTIVE_PRIVACY_REQUEST_STATUSES = frozenset(
    {
        PrivacyRequestStatus.SUBMITTED,
        PrivacyRequestStatus.IDENTITY_VERIFICATION,
        PrivacyRequestStatus.PENDING_DECISION,
        PrivacyRequestStatus.APPROVED,
        PrivacyRequestStatus.SCHEDULED,
        PrivacyRequestStatus.FAILED,
    }
)
TERMINAL_PRIVACY_REQUEST_STATUSES = frozenset(
    {
        PrivacyRequestStatus.FULFILLED,
        PrivacyRequestStatus.DENIED,
        PrivacyRequestStatus.CANCELED,
    }
)

CUSTOMER_CANCELABLE_PRIVACY_REQUEST_STATUSES = frozenset(
    {
        PrivacyRequestStatus.SUBMITTED,
        PrivacyRequestStatus.IDENTITY_VERIFICATION,
        PrivacyRequestStatus.PENDING_DECISION,
    }
)

PRIVACY_REQUEST_TRANSITIONS: dict[PrivacyRequestStatus, frozenset[PrivacyRequestStatus]] = {
    PrivacyRequestStatus.SUBMITTED: frozenset(
        {
            PrivacyRequestStatus.IDENTITY_VERIFICATION,
            PrivacyRequestStatus.CANCELED,
        }
    ),
    PrivacyRequestStatus.IDENTITY_VERIFICATION: frozenset(
        {
            PrivacyRequestStatus.PENDING_DECISION,
            PrivacyRequestStatus.DENIED,
            PrivacyRequestStatus.CANCELED,
        }
    ),
    PrivacyRequestStatus.PENDING_DECISION: frozenset(
        {
            PrivacyRequestStatus.APPROVED,
            PrivacyRequestStatus.DENIED,
            PrivacyRequestStatus.CANCELED,
        }
    ),
    PrivacyRequestStatus.APPROVED: frozenset({PrivacyRequestStatus.SCHEDULED}),
    PrivacyRequestStatus.SCHEDULED: frozenset(
        {
            PrivacyRequestStatus.FULFILLED,
            PrivacyRequestStatus.FAILED,
        }
    ),
    PrivacyRequestStatus.FAILED: frozenset(
        {
            PrivacyRequestStatus.SCHEDULED,
            PrivacyRequestStatus.DENIED,
        }
    ),
    PrivacyRequestStatus.FULFILLED: frozenset(),
    PrivacyRequestStatus.DENIED: frozenset(),
    PrivacyRequestStatus.CANCELED: frozenset(),
}


def assert_privacy_transition(
    *,
    from_status: PrivacyRequestStatus,
    to_status: PrivacyRequestStatus,
) -> None:
    if from_status == to_status:
        return
    if to_status not in PRIVACY_REQUEST_TRANSITIONS[from_status]:
        raise InvalidPrivacyRequestTransitionError(
            f"Invalid privacy request transition: {from_status.value} -> {to_status.value}"
        )
