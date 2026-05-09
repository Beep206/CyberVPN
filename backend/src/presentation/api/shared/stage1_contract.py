"""Canonical S1 status and error contract for backend, UI and support flows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums.enums import (
    AccessDeliveryChannelStatus,
    DeviceCredentialStatus,
    EntitlementGrantStatus,
    PaymentAttemptStatus,
    PaymentStatus,
    ProvisioningProfileStatus,
    ServiceIdentityStatus,
    UserStatus,
)

JsonScalar = str | int | float | bool | None


class Stage1Surface(StrEnum):
    """Launch-critical S1 product/backend surface."""

    AUTH = "auth"
    PAYMENT = "payment"
    PROVISIONING = "provisioning"
    SUPPORT = "support"
    SYSTEM = "system"
    VALIDATION = "validation"


class Stage1AccessState(StrEnum):
    """Customer-facing access/subscription state used by S1 UI and support."""

    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    TRIAL_AVAILABLE = "trial_available"
    TRIAL_ACTIVE = "trial_active"
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    LIMITED = "limited"
    NO_ACCESS = "no_access"
    PAYMENT_PENDING = "payment_pending"
    PROVISIONING_PENDING = "provisioning_pending"


class Stage1PaymentState(StrEnum):
    """Canonical payment state for web, Telegram, admin and support views."""

    NOT_STARTED = "not_started"
    QUOTE_READY = "quote_ready"
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    ORPHAN_REVIEW_REQUIRED = "orphan_review_required"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class Stage1ProvisioningState(StrEnum):
    """Canonical VPN provisioning/readiness state for Remnawave-backed access."""

    NOT_REQUIRED = "not_required"
    QUEUED = "queued"
    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    RETRYING = "retrying"
    FAILED = "failed"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    REMNAWAVE_UNAVAILABLE = "remnawave_unavailable"


class Stage1SupportState(StrEnum):
    """Support/escalation state visible to admin/support tooling."""

    NONE = "none"
    SELF_SERVICE = "self_service"
    SUPPORT_REVIEW = "support_review"
    OPS_ESCALATION = "ops_escalation"
    RESOLVED = "resolved"


class Stage1ErrorCode(StrEnum):
    """Stable S1 error codes. UI copy may translate these values, but must not invent new ones."""

    VALIDATION_ERROR = "validation_error"
    AUTH_INVALID_CREDENTIALS = "auth_invalid_credentials"
    AUTH_SESSION_EXPIRED = "auth_session_expired"
    AUTH_ACCOUNT_LOCKED = "auth_account_locked"
    AUTH_EMAIL_VERIFICATION_REQUIRED = "auth_email_verification_required"
    AUTH_2FA_REQUIRED = "auth_2fa_required"
    AUTH_RATE_LIMITED = "auth_rate_limited"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_CANCELLED = "payment_cancelled"
    PAYMENT_EXPIRED = "payment_expired"
    PAYMENT_PROVIDER_UNAVAILABLE = "payment_provider_unavailable"
    PAYMENT_ORPHAN_REVIEW_REQUIRED = "payment_orphan_review_required"
    PROVISIONING_PENDING = "provisioning_pending"
    PROVISIONING_RETRYING = "provisioning_retrying"
    PROVISIONING_FAILED = "provisioning_failed"
    PROVISIONING_RECONCILIATION_REQUIRED = "provisioning_reconciliation_required"
    REMNAWAVE_UNAVAILABLE = "remnawave_unavailable"
    SUPPORT_ESCALATION_REQUIRED = "support_escalation_required"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True, slots=True)
class Stage1ErrorSpec:
    """Matrix row for a canonical S1 error code."""

    http_status: int
    surface: Stage1Surface
    message: str
    user_action: str
    retryable: bool = False
    support_escalation: bool = False


class Stage1CanonicalErrorResponse(BaseModel):
    """Stable error response body for S1 APIs.

    Existing endpoints may still return legacy `detail` responses until migrated.
    New and touched S1 endpoints should use this shape.
    """

    model_config = ConfigDict(use_enum_values=True)

    code: Stage1ErrorCode = Field(..., description="Stable machine-readable S1 error code.")
    message: str = Field(..., description="Safe user-facing message.")
    surface: Stage1Surface = Field(..., description="S1 surface that owns the error.")
    http_status: int = Field(..., ge=100, le=599, description="HTTP status used by the response.")
    user_action: str = Field(..., description="Recommended user/support action.")
    retryable: bool = Field(..., description="Whether automatic retry is allowed.")
    support_escalation: bool = Field(..., description="Whether support/ops escalation is required.")
    request_id: str | None = Field(default=None, description="Request id, when available.")
    details: dict[str, JsonScalar] = Field(default_factory=dict, description="Redacted structured context.")


class Stage1FlowStatusResponse(BaseModel):
    """Composite S1 state for customer dashboard, Telegram Mini App and support views."""

    model_config = ConfigDict(use_enum_values=True)

    access_state: Stage1AccessState
    payment_state: Stage1PaymentState = Stage1PaymentState.NOT_STARTED
    provisioning_state: Stage1ProvisioningState = Stage1ProvisioningState.NOT_REQUIRED
    support_state: Stage1SupportState = Stage1SupportState.NONE
    user_action: str | None = None
    support_escalation: bool = False
    details: dict[str, JsonScalar] = Field(default_factory=dict)


STAGE1_ERROR_MATRIX: dict[Stage1ErrorCode, Stage1ErrorSpec] = {
    Stage1ErrorCode.VALIDATION_ERROR: Stage1ErrorSpec(
        http_status=422,
        surface=Stage1Surface.VALIDATION,
        message="Request validation failed.",
        user_action="Fix the highlighted fields and try again.",
    ),
    Stage1ErrorCode.AUTH_INVALID_CREDENTIALS: Stage1ErrorSpec(
        http_status=401,
        surface=Stage1Surface.AUTH,
        message="Invalid email, username or password.",
        user_action="Check credentials or use password recovery.",
    ),
    Stage1ErrorCode.AUTH_SESSION_EXPIRED: Stage1ErrorSpec(
        http_status=401,
        surface=Stage1Surface.AUTH,
        message="Session expired.",
        user_action="Sign in again.",
    ),
    Stage1ErrorCode.AUTH_ACCOUNT_LOCKED: Stage1ErrorSpec(
        http_status=423,
        surface=Stage1Surface.AUTH,
        message="Account access is temporarily locked.",
        user_action="Contact support if the lock does not clear.",
        support_escalation=True,
    ),
    Stage1ErrorCode.AUTH_EMAIL_VERIFICATION_REQUIRED: Stage1ErrorSpec(
        http_status=403,
        surface=Stage1Surface.AUTH,
        message="Email verification is required.",
        user_action="Verify your email address before continuing.",
    ),
    Stage1ErrorCode.AUTH_2FA_REQUIRED: Stage1ErrorSpec(
        http_status=403,
        surface=Stage1Surface.AUTH,
        message="Two-factor authentication is required.",
        user_action="Complete the two-factor challenge.",
    ),
    Stage1ErrorCode.AUTH_RATE_LIMITED: Stage1ErrorSpec(
        http_status=429,
        surface=Stage1Surface.AUTH,
        message="Too many authentication attempts.",
        user_action="Wait before trying again.",
        retryable=True,
    ),
    Stage1ErrorCode.PERMISSION_DENIED: Stage1ErrorSpec(
        http_status=403,
        surface=Stage1Surface.AUTH,
        message="Permission denied.",
        user_action="Use an account with the required role or contact support.",
    ),
    Stage1ErrorCode.NOT_FOUND: Stage1ErrorSpec(
        http_status=404,
        surface=Stage1Surface.SYSTEM,
        message="Resource not found.",
        user_action="Refresh and try again, or contact support.",
    ),
    Stage1ErrorCode.RATE_LIMITED: Stage1ErrorSpec(
        http_status=429,
        surface=Stage1Surface.SYSTEM,
        message="Too many requests.",
        user_action="Wait before trying again.",
        retryable=True,
    ),
    Stage1ErrorCode.PAYMENT_PENDING: Stage1ErrorSpec(
        http_status=202,
        surface=Stage1Surface.PAYMENT,
        message="Payment is still pending.",
        user_action="Wait for the payment provider to confirm the payment.",
        retryable=True,
    ),
    Stage1ErrorCode.PAYMENT_FAILED: Stage1ErrorSpec(
        http_status=402,
        surface=Stage1Surface.PAYMENT,
        message="Payment failed.",
        user_action="Try another payment method or contact support.",
    ),
    Stage1ErrorCode.PAYMENT_CANCELLED: Stage1ErrorSpec(
        http_status=409,
        surface=Stage1Surface.PAYMENT,
        message="Payment was cancelled.",
        user_action="Create a new invoice if you still want to continue.",
    ),
    Stage1ErrorCode.PAYMENT_EXPIRED: Stage1ErrorSpec(
        http_status=409,
        surface=Stage1Surface.PAYMENT,
        message="Payment invoice expired.",
        user_action="Create a new invoice.",
    ),
    Stage1ErrorCode.PAYMENT_PROVIDER_UNAVAILABLE: Stage1ErrorSpec(
        http_status=503,
        surface=Stage1Surface.PAYMENT,
        message="Payment provider is temporarily unavailable.",
        user_action="Try again later or use another tested payment method.",
        retryable=True,
    ),
    Stage1ErrorCode.PAYMENT_ORPHAN_REVIEW_REQUIRED: Stage1ErrorSpec(
        http_status=409,
        surface=Stage1Surface.PAYMENT,
        message="Payment was received, but access is not ready yet.",
        user_action="Support must review and restore access within the S1 orphan-payment SLA.",
        retryable=True,
        support_escalation=True,
    ),
    Stage1ErrorCode.PROVISIONING_PENDING: Stage1ErrorSpec(
        http_status=202,
        surface=Stage1Surface.PROVISIONING,
        message="VPN access provisioning is pending.",
        user_action="Wait while access is being prepared.",
        retryable=True,
    ),
    Stage1ErrorCode.PROVISIONING_RETRYING: Stage1ErrorSpec(
        http_status=202,
        surface=Stage1Surface.PROVISIONING,
        message="VPN access provisioning is retrying.",
        user_action="Wait for the retry to complete.",
        retryable=True,
    ),
    Stage1ErrorCode.PROVISIONING_FAILED: Stage1ErrorSpec(
        http_status=502,
        surface=Stage1Surface.PROVISIONING,
        message="VPN access provisioning failed.",
        user_action="Contact support if access is not restored automatically.",
        retryable=True,
        support_escalation=True,
    ),
    Stage1ErrorCode.PROVISIONING_RECONCILIATION_REQUIRED: Stage1ErrorSpec(
        http_status=409,
        surface=Stage1Surface.PROVISIONING,
        message="VPN access state requires reconciliation.",
        user_action="Support or ops must reconcile payment and VPN access state.",
        retryable=True,
        support_escalation=True,
    ),
    Stage1ErrorCode.REMNAWAVE_UNAVAILABLE: Stage1ErrorSpec(
        http_status=503,
        surface=Stage1Surface.PROVISIONING,
        message="VPN control plane is temporarily unavailable.",
        user_action="Wait for automatic retry or contact support if access is urgent.",
        retryable=True,
        support_escalation=True,
    ),
    Stage1ErrorCode.SUPPORT_ESCALATION_REQUIRED: Stage1ErrorSpec(
        http_status=409,
        surface=Stage1Surface.SUPPORT,
        message="Support escalation is required.",
        user_action="Support must review this case manually.",
        support_escalation=True,
    ),
    Stage1ErrorCode.INTERNAL_ERROR: Stage1ErrorSpec(
        http_status=500,
        surface=Stage1Surface.SYSTEM,
        message="Unexpected service error.",
        user_action="Try again later or contact support with the request id.",
        retryable=True,
    ),
}


USER_STATUS_TO_STAGE1_ACCESS_STATE: dict[UserStatus, Stage1AccessState] = {
    UserStatus.ACTIVE: Stage1AccessState.ACTIVE,
    UserStatus.DISABLED: Stage1AccessState.SUSPENDED,
    UserStatus.LIMITED: Stage1AccessState.LIMITED,
    UserStatus.EXPIRED: Stage1AccessState.EXPIRED,
}

PAYMENT_STATUS_TO_STAGE1_STATE: dict[PaymentStatus, Stage1PaymentState] = {
    PaymentStatus.PENDING: Stage1PaymentState.PENDING,
    PaymentStatus.COMPLETED: Stage1PaymentState.PAID,
    PaymentStatus.FAILED: Stage1PaymentState.FAILED,
    PaymentStatus.REFUNDED: Stage1PaymentState.REFUNDED,
}

PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE: dict[PaymentAttemptStatus, Stage1PaymentState] = {
    PaymentAttemptStatus.PENDING: Stage1PaymentState.PENDING,
    PaymentAttemptStatus.PROCESSING: Stage1PaymentState.PROCESSING,
    PaymentAttemptStatus.SUCCEEDED: Stage1PaymentState.PAID,
    PaymentAttemptStatus.FAILED: Stage1PaymentState.FAILED,
    PaymentAttemptStatus.EXPIRED: Stage1PaymentState.EXPIRED,
    PaymentAttemptStatus.CANCELLED: Stage1PaymentState.CANCELLED,
}

SERVICE_IDENTITY_STATUS_TO_STAGE1_PROVISIONING_STATE: dict[ServiceIdentityStatus, Stage1ProvisioningState] = {
    ServiceIdentityStatus.ACTIVE: Stage1ProvisioningState.READY,
    ServiceIdentityStatus.SUSPENDED: Stage1ProvisioningState.SUSPENDED,
    ServiceIdentityStatus.REVOKED: Stage1ProvisioningState.FAILED,
}

PROVISIONING_PROFILE_STATUS_TO_STAGE1_PROVISIONING_STATE: dict[ProvisioningProfileStatus, Stage1ProvisioningState] = {
    ProvisioningProfileStatus.DRAFT: Stage1ProvisioningState.PENDING,
    ProvisioningProfileStatus.ACTIVE: Stage1ProvisioningState.READY,
    ProvisioningProfileStatus.ARCHIVED: Stage1ProvisioningState.FAILED,
}

ENTITLEMENT_GRANT_STATUS_TO_STAGE1_ACCESS_STATE: dict[EntitlementGrantStatus, Stage1AccessState] = {
    EntitlementGrantStatus.PENDING: Stage1AccessState.PROVISIONING_PENDING,
    EntitlementGrantStatus.ACTIVE: Stage1AccessState.ACTIVE,
    EntitlementGrantStatus.SUSPENDED: Stage1AccessState.SUSPENDED,
    EntitlementGrantStatus.REVOKED: Stage1AccessState.NO_ACCESS,
    EntitlementGrantStatus.EXPIRED: Stage1AccessState.EXPIRED,
}

DEVICE_CREDENTIAL_STATUS_TO_STAGE1_PROVISIONING_STATE: dict[DeviceCredentialStatus, Stage1ProvisioningState] = {
    DeviceCredentialStatus.ACTIVE: Stage1ProvisioningState.READY,
    DeviceCredentialStatus.REVOKED: Stage1ProvisioningState.FAILED,
    DeviceCredentialStatus.EXPIRED: Stage1ProvisioningState.EXPIRED,
}

ACCESS_DELIVERY_STATUS_TO_STAGE1_PROVISIONING_STATE: dict[AccessDeliveryChannelStatus, Stage1ProvisioningState] = {
    AccessDeliveryChannelStatus.ACTIVE: Stage1ProvisioningState.READY,
    AccessDeliveryChannelStatus.SUSPENDED: Stage1ProvisioningState.SUSPENDED,
    AccessDeliveryChannelStatus.ARCHIVED: Stage1ProvisioningState.FAILED,
}


def build_stage1_error_response(
    code: Stage1ErrorCode,
    *,
    request_id: str | None = None,
    message: str | None = None,
    details: dict[str, JsonScalar] | None = None,
) -> Stage1CanonicalErrorResponse:
    """Build a redacted canonical S1 error response from the approved matrix."""

    spec = STAGE1_ERROR_MATRIX[code]
    return Stage1CanonicalErrorResponse(
        code=code,
        message=message or spec.message,
        surface=spec.surface,
        http_status=spec.http_status,
        user_action=spec.user_action,
        retryable=spec.retryable,
        support_escalation=spec.support_escalation,
        request_id=request_id,
        details=details or {},
    )


__all__ = [
    "ACCESS_DELIVERY_STATUS_TO_STAGE1_PROVISIONING_STATE",
    "DEVICE_CREDENTIAL_STATUS_TO_STAGE1_PROVISIONING_STATE",
    "ENTITLEMENT_GRANT_STATUS_TO_STAGE1_ACCESS_STATE",
    "PAYMENT_ATTEMPT_STATUS_TO_STAGE1_STATE",
    "PAYMENT_STATUS_TO_STAGE1_STATE",
    "PROVISIONING_PROFILE_STATUS_TO_STAGE1_PROVISIONING_STATE",
    "SERVICE_IDENTITY_STATUS_TO_STAGE1_PROVISIONING_STATE",
    "STAGE1_ERROR_MATRIX",
    "USER_STATUS_TO_STAGE1_ACCESS_STATE",
    "Stage1AccessState",
    "Stage1CanonicalErrorResponse",
    "Stage1ErrorCode",
    "Stage1ErrorSpec",
    "Stage1FlowStatusResponse",
    "Stage1PaymentState",
    "Stage1ProvisioningState",
    "Stage1SupportState",
    "Stage1Surface",
    "build_stage1_error_response",
]
