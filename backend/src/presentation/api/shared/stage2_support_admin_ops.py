"""S2 support/admin operations contract.

The module is side-effect free and describes what support may diagnose, which
actions require escalation, and which fields must never leave protected admin
surfaces in raw form during the public B2C release.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.domain.enums import AdminRole
from src.presentation.api.shared.stage1_support_templates import Stage1SupportTemplateId

S2_SUPPORT_EMAIL = "support@cyber-vpn.net"
S2_REFUND_EMAIL = "refund@cyber-vpn.net"
S2_ABUSE_EMAIL = "abuse@cyber-vpn.net"

S2_SUPPORT_P0_ACK_MINUTES = 15
S2_SUPPORT_P1_ACK_MINUTES = 60
S2_SUPPORT_FIRST_RESPONSE_HOURS = 12
S2_PAID_NO_ACCESS_MAX_AGE_HOURS = 24

S2_SUPPORT_FORBIDDEN_OUTPUT_FIELDS = (
    "password",
    "password_hash",
    "otp",
    "totp",
    "two_factor",
    "refresh_token",
    "access_token",
    "jwt",
    "telegram_init_data",
    "provider_secret",
    "provider_token",
    "webhook_signature",
    "raw_provider_payload",
    "subscription_url",
    "config_link",
    "raw_config",
    "vless",
    "private_key",
    "seed_phrase",
    "card_number",
    "cvv",
    "cvc",
)


class S2SupportIssueType(StrEnum):
    """Support issue groups required before S2 public release."""

    CANNOT_LOGIN = "cannot_login"
    PAYMENT_SUCCEEDED_NO_ACCESS = "payment_succeeded_no_access"
    VPN_DOES_NOT_CONNECT = "vpn_does_not_connect"
    REFUND_REQUEST = "refund_request"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    GROWTH_OR_RECURRING_ISSUE = "growth_or_recurring_issue"


class S2SupportLookup(StrEnum):
    """Redacted lookup surfaces support/admin may use for one case."""

    CUSTOMER = "customer_lookup"
    AUTH_DIAGNOSTICS = "auth_diagnostics"
    PAYMENT = "payment_lookup"
    SUBSCRIPTION = "subscription_lookup"
    PROVISIONING = "provisioning_lookup"
    REFUND_DISPUTE = "refund_dispute_lookup"
    GROWTH = "growth_reward_lookup"
    AUDIT_TIMELINE = "audit_timeline"


class S2SupportAction(StrEnum):
    """Support/admin actions referenced by the S2 runbook."""

    READ_DIAGNOSTICS = "read_diagnostics"
    CREATE_TICKET = "create_ticket"
    ADD_STAFF_NOTE = "add_staff_note"
    PAYMENT_RECONCILIATION_REVIEW = "payment_reconciliation_review"
    REFUND_REVIEW = "refund_review"
    MANUAL_SUPPORT_GRANT = "manual_support_grant"
    REPROVISION_OR_RESYNC = "reprovision_or_resync"
    VPN_CREDENTIAL_REGENERATION = "vpn_credential_regeneration"
    ACCOUNT_RECOVERY = "account_recovery"
    GROWTH_REVERSAL = "growth_reversal"


class S2SupportReadinessState(StrEnum):
    """Overall readiness for S2 support/admin operations."""

    READY = "ready"
    READY_WITH_LIMITS = "ready_with_limits"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class S2SupportIssueContract:
    """Support issue routing and lookup contract."""

    issue_type: S2SupportIssueType
    template_id: Stage1SupportTemplateId | None
    priority: str
    contact: str
    required_lookups: tuple[S2SupportLookup, ...]
    allowed_actions: tuple[S2SupportAction, ...]
    escalation_queue: str
    ack_minutes: int | None
    first_response_hours: int


@dataclass(frozen=True, slots=True)
class S2SupportActionDecision:
    """Role decision for a support/admin action."""

    role: AdminRole
    action: S2SupportAction
    allowed: bool
    audit_required: bool
    reason: str


@dataclass(frozen=True, slots=True)
class S2SupportAdminReadinessSnapshot:
    """Observed support/admin operational prerequisites."""

    support_queue_available: bool
    customer_lookup_available: bool
    payment_lookup_available: bool
    subscription_lookup_available: bool
    provisioning_lookup_available: bool
    audit_log_available: bool
    manual_grants_audited: bool
    dangerous_actions_protected: bool
    support_email_configured: bool
    refund_email_configured: bool
    abuse_email_configured: bool
    primary_on_call_set: bool
    backup_on_call_set: bool
    primary_and_backup_split: bool = False


@dataclass(frozen=True, slots=True)
class S2SupportAdminReadinessDecision:
    """Safe S2 support/admin readiness result."""

    state: S2SupportReadinessState
    ready_for_public_release: bool
    issues: tuple[str, ...]
    recommendations: tuple[str, ...]


S2_SUPPORT_ISSUE_CONTRACTS: dict[S2SupportIssueType, S2SupportIssueContract] = {
    S2SupportIssueType.CANNOT_LOGIN: S2SupportIssueContract(
        issue_type=S2SupportIssueType.CANNOT_LOGIN,
        template_id=None,
        priority="P1",
        contact=S2_SUPPORT_EMAIL,
        required_lookups=(
            S2SupportLookup.CUSTOMER,
            S2SupportLookup.AUTH_DIAGNOSTICS,
            S2SupportLookup.AUDIT_TIMELINE,
        ),
        allowed_actions=(
            S2SupportAction.READ_DIAGNOSTICS,
            S2SupportAction.CREATE_TICKET,
            S2SupportAction.ADD_STAFF_NOTE,
            S2SupportAction.ACCOUNT_RECOVERY,
        ),
        escalation_queue="s2_auth_support_review",
        ack_minutes=S2_SUPPORT_P1_ACK_MINUTES,
        first_response_hours=S2_SUPPORT_FIRST_RESPONSE_HOURS,
    ),
    S2SupportIssueType.PAYMENT_SUCCEEDED_NO_ACCESS: S2SupportIssueContract(
        issue_type=S2SupportIssueType.PAYMENT_SUCCEEDED_NO_ACCESS,
        template_id=Stage1SupportTemplateId.PAID_NO_ACCESS,
        priority="P0",
        contact=S2_SUPPORT_EMAIL,
        required_lookups=(
            S2SupportLookup.CUSTOMER,
            S2SupportLookup.PAYMENT,
            S2SupportLookup.SUBSCRIPTION,
            S2SupportLookup.PROVISIONING,
            S2SupportLookup.AUDIT_TIMELINE,
        ),
        allowed_actions=(
            S2SupportAction.READ_DIAGNOSTICS,
            S2SupportAction.CREATE_TICKET,
            S2SupportAction.PAYMENT_RECONCILIATION_REVIEW,
            S2SupportAction.REPROVISION_OR_RESYNC,
            S2SupportAction.MANUAL_SUPPORT_GRANT,
        ),
        escalation_queue="s2_paid_no_access_review",
        ack_minutes=S2_SUPPORT_P0_ACK_MINUTES,
        first_response_hours=S2_SUPPORT_FIRST_RESPONSE_HOURS,
    ),
    S2SupportIssueType.VPN_DOES_NOT_CONNECT: S2SupportIssueContract(
        issue_type=S2SupportIssueType.VPN_DOES_NOT_CONNECT,
        template_id=Stage1SupportTemplateId.VPN_NOT_CONNECTING,
        priority="P1",
        contact=S2_SUPPORT_EMAIL,
        required_lookups=(
            S2SupportLookup.CUSTOMER,
            S2SupportLookup.SUBSCRIPTION,
            S2SupportLookup.PROVISIONING,
            S2SupportLookup.AUDIT_TIMELINE,
        ),
        allowed_actions=(
            S2SupportAction.READ_DIAGNOSTICS,
            S2SupportAction.CREATE_TICKET,
            S2SupportAction.REPROVISION_OR_RESYNC,
            S2SupportAction.VPN_CREDENTIAL_REGENERATION,
        ),
        escalation_queue="s2_vpn_connectivity_support",
        ack_minutes=S2_SUPPORT_P1_ACK_MINUTES,
        first_response_hours=S2_SUPPORT_FIRST_RESPONSE_HOURS,
    ),
    S2SupportIssueType.REFUND_REQUEST: S2SupportIssueContract(
        issue_type=S2SupportIssueType.REFUND_REQUEST,
        template_id=Stage1SupportTemplateId.REFUND_REQUEST,
        priority="P1",
        contact=S2_REFUND_EMAIL,
        required_lookups=(
            S2SupportLookup.CUSTOMER,
            S2SupportLookup.PAYMENT,
            S2SupportLookup.REFUND_DISPUTE,
            S2SupportLookup.AUDIT_TIMELINE,
        ),
        allowed_actions=(
            S2SupportAction.READ_DIAGNOSTICS,
            S2SupportAction.CREATE_TICKET,
            S2SupportAction.REFUND_REVIEW,
        ),
        escalation_queue="s2_payment_finance_review",
        ack_minutes=S2_SUPPORT_P1_ACK_MINUTES,
        first_response_hours=S2_SUPPORT_FIRST_RESPONSE_HOURS,
    ),
    S2SupportIssueType.SUBSCRIPTION_EXPIRED: S2SupportIssueContract(
        issue_type=S2SupportIssueType.SUBSCRIPTION_EXPIRED,
        template_id=Stage1SupportTemplateId.EXPIRED_SUBSCRIPTION,
        priority="P2",
        contact=S2_SUPPORT_EMAIL,
        required_lookups=(
            S2SupportLookup.CUSTOMER,
            S2SupportLookup.PAYMENT,
            S2SupportLookup.SUBSCRIPTION,
            S2SupportLookup.AUDIT_TIMELINE,
        ),
        allowed_actions=(
            S2SupportAction.READ_DIAGNOSTICS,
            S2SupportAction.CREATE_TICKET,
            S2SupportAction.PAYMENT_RECONCILIATION_REVIEW,
        ),
        escalation_queue="s2_customer_support",
        ack_minutes=None,
        first_response_hours=S2_SUPPORT_FIRST_RESPONSE_HOURS,
    ),
    S2SupportIssueType.GROWTH_OR_RECURRING_ISSUE: S2SupportIssueContract(
        issue_type=S2SupportIssueType.GROWTH_OR_RECURRING_ISSUE,
        template_id=None,
        priority="P1",
        contact=S2_SUPPORT_EMAIL,
        required_lookups=(
            S2SupportLookup.CUSTOMER,
            S2SupportLookup.PAYMENT,
            S2SupportLookup.GROWTH,
            S2SupportLookup.AUDIT_TIMELINE,
        ),
        allowed_actions=(
            S2SupportAction.READ_DIAGNOSTICS,
            S2SupportAction.CREATE_TICKET,
            S2SupportAction.GROWTH_REVERSAL,
        ),
        escalation_queue="s2_growth_billing_support",
        ack_minutes=S2_SUPPORT_P1_ACK_MINUTES,
        first_response_hours=S2_SUPPORT_FIRST_RESPONSE_HOURS,
    ),
}

S2_SUPPORT_REQUIRED_AUDIT_ACTIONS = (
    "customer_staff_note_created",
    "customer_vpn_enabled",
    "customer_vpn_disabled",
    "customer_vpn_credentials_regenerated",
    "customer_device_revoked",
    "customer_devices_revoked_all",
    "customer_password_reset",
    "customer_subscription_manual_granted",
    "customer_subscription_resynced",
    "customer_operations.verify_payout_account",
    "customer_operations.suspend_payout_account",
    "customer_operations.approve_payout_instruction",
    "customer_operations.reject_payout_instruction",
)


def list_s2_support_issue_contracts() -> tuple[S2SupportIssueContract, ...]:
    """Return S2 support contracts in stable runbook order."""

    return tuple(S2_SUPPORT_ISSUE_CONTRACTS[issue_type] for issue_type in S2SupportIssueType)


def get_s2_support_issue_contract(issue_type: S2SupportIssueType | str) -> S2SupportIssueContract:
    """Resolve a support issue contract by stable identifier."""

    resolved = issue_type if isinstance(issue_type, S2SupportIssueType) else S2SupportIssueType(str(issue_type))
    return S2_SUPPORT_ISSUE_CONTRACTS[resolved]


def decide_s2_support_action(role: AdminRole | str, action: S2SupportAction | str) -> S2SupportActionDecision:
    """Evaluate whether a role may perform one support/admin action."""

    resolved_role = role if isinstance(role, AdminRole) else AdminRole(str(role))
    resolved_action = action if isinstance(action, S2SupportAction) else S2SupportAction(str(action))
    allowed = _role_allows_action(resolved_role, resolved_action)
    return S2SupportActionDecision(
        role=resolved_role,
        action=resolved_action,
        allowed=allowed,
        audit_required=_action_requires_audit(resolved_action),
        reason=_action_reason(resolved_action, allowed),
    )


def evaluate_s2_support_admin_readiness(
    snapshot: S2SupportAdminReadinessSnapshot,
) -> S2SupportAdminReadinessDecision:
    """Evaluate S2 support/admin readiness without accessing production data."""

    issues: list[str] = []
    recommendations: list[str] = []
    hard_checks = {
        "support_queue_unavailable": snapshot.support_queue_available,
        "customer_lookup_unavailable": snapshot.customer_lookup_available,
        "payment_lookup_unavailable": snapshot.payment_lookup_available,
        "subscription_lookup_unavailable": snapshot.subscription_lookup_available,
        "provisioning_lookup_unavailable": snapshot.provisioning_lookup_available,
        "audit_log_unavailable": snapshot.audit_log_available,
        "manual_grants_not_audited": snapshot.manual_grants_audited,
        "dangerous_actions_not_protected": snapshot.dangerous_actions_protected,
        "support_email_missing": snapshot.support_email_configured,
        "refund_email_missing": snapshot.refund_email_configured,
        "abuse_email_missing": snapshot.abuse_email_configured,
        "primary_on_call_missing": snapshot.primary_on_call_set,
        "backup_on_call_missing": snapshot.backup_on_call_set,
    }
    issues.extend(issue for issue, passed in hard_checks.items() if not passed)

    if not snapshot.primary_and_backup_split:
        recommendations.append("split_primary_and_backup_support_on_call_before_unrestricted_s2_opening")

    if issues:
        state = S2SupportReadinessState.BLOCKED
    elif recommendations:
        state = S2SupportReadinessState.READY_WITH_LIMITS
    else:
        state = S2SupportReadinessState.READY

    return S2SupportAdminReadinessDecision(
        state=state,
        ready_for_public_release=state != S2SupportReadinessState.BLOCKED,
        issues=tuple(issues),
        recommendations=tuple(recommendations),
    )


def redact_s2_support_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields and raw config values from support diagnostics."""

    return {str(key): _redact_value(str(key), value) for key, value in payload.items()}


def _role_allows_action(role: AdminRole, action: S2SupportAction) -> bool:
    if action in {
        S2SupportAction.READ_DIAGNOSTICS,
        S2SupportAction.CREATE_TICKET,
        S2SupportAction.ADD_STAFF_NOTE,
    }:
        return has_permission(role, Permission.USER_READ)
    if action == S2SupportAction.PAYMENT_RECONCILIATION_REVIEW:
        return has_permission(role, Permission.PAYMENT_READ)
    if action == S2SupportAction.REFUND_REVIEW:
        return role in {AdminRole.FINANCE, AdminRole.ADMIN, AdminRole.SUPER_ADMIN, AdminRole.OWNER_SUPER_ADMIN}
    if action == S2SupportAction.MANUAL_SUPPORT_GRANT:
        return has_permission(role, Permission.SUBSCRIPTION_CREATE)
    if action == S2SupportAction.VPN_CREDENTIAL_REGENERATION:
        return has_permission(role, Permission.VPN_CREDENTIAL_REGENERATE)
    if action == S2SupportAction.REPROVISION_OR_RESYNC:
        return has_permission(role, Permission.USER_UPDATE) or has_permission(role, Permission.SUBSCRIPTION_CREATE)
    if action == S2SupportAction.ACCOUNT_RECOVERY:
        return has_permission(role, Permission.USER_UPDATE)
    if action == S2SupportAction.GROWTH_REVERSAL:
        return role in {AdminRole.ADMIN, AdminRole.SUPER_ADMIN, AdminRole.OWNER_SUPER_ADMIN}
    return False


def _action_requires_audit(action: S2SupportAction) -> bool:
    return action not in {
        S2SupportAction.READ_DIAGNOSTICS,
        S2SupportAction.CREATE_TICKET,
    }


def _action_reason(action: S2SupportAction, allowed: bool) -> str:
    if allowed:
        return f"{action.value}_allowed_by_role_contract"
    return f"{action.value}_requires_privileged_role_or_permission"


def _redact_value(key: str, value: Any) -> Any:
    lowered_key = key.lower()
    if any(part in lowered_key for part in S2_SUPPORT_FORBIDDEN_OUTPUT_FIELDS):
        return "[REDACTED]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Mapping):
        return redact_s2_support_payload(value)
    if isinstance(value, list | tuple | set):
        return [_redact_value(key, item) for item in value]
    if isinstance(value, str) and (
        value.startswith("vless://")
        or "/api/sub/" in value
        or "subscription" in value.lower()
        or "config" in value.lower()
    ):
        return "[REDACTED]"
    return value
