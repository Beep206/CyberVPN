"""Stage 1 refund and payment-dispute process contract.

The policy is intentionally narrower than the generic admin hierarchy:
support may intake and escalate cases, but only finance/admin roles may change
refund or dispute financial state in S1.
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException, status

from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider
from src.presentation.dependencies.auth import get_current_active_user


class Stage1RefundProviderMode(StrEnum):
    """How an S1 provider may execute or reconcile refunds before go-live."""

    MANUAL_FINANCE_REVIEW = "manual_finance_review"
    TELEGRAM_STARS_API_AFTER_EVIDENCE = "telegram_stars_api_after_evidence"
    PROVIDER_API_AFTER_EVIDENCE = "provider_api_after_evidence"
    PROVIDER_SUPPORT_OR_MANUAL_PAYOUT = "provider_support_or_manual_payout"


class Stage1RefundDisputeAction(StrEnum):
    """Allowed S1 process actions."""

    CUSTOMER_REFUND_REQUEST = "customer_refund_request"
    SUPPORT_INTAKE_ESCALATION = "support_intake_escalation"
    FINANCE_REFUND_REVIEW = "finance_refund_review"
    FINANCE_DISPUTE_RECONCILIATION = "finance_dispute_reconciliation"
    ADMIN_OVERRIDE = "admin_override"


STAGE1_REFUND_DISPUTE_REVIEW_ROLES = frozenset(
    {
        AdminRole.FINANCE,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    }
)

STAGE1_REFUND_DISPUTE_SUPPORT_INTAKE_ROLES = frozenset(
    {
        AdminRole.SUPPORT,
        AdminRole.FINANCE,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    }
)

STAGE1_REFUND_DISPUTE_PROVIDER_MODES: dict[Stage1PaymentProvider, Stage1RefundProviderMode] = {
    Stage1PaymentProvider.PAYRAM: Stage1RefundProviderMode.PROVIDER_SUPPORT_OR_MANUAL_PAYOUT,
    Stage1PaymentProvider.NOWPAYMENTS: Stage1RefundProviderMode.PROVIDER_SUPPORT_OR_MANUAL_PAYOUT,
    Stage1PaymentProvider.CRYPTOBOT: Stage1RefundProviderMode.MANUAL_FINANCE_REVIEW,
    Stage1PaymentProvider.TELEGRAM_STARS: Stage1RefundProviderMode.TELEGRAM_STARS_API_AFTER_EVIDENCE,
    Stage1PaymentProvider.DIGISELLER: Stage1RefundProviderMode.PROVIDER_API_AFTER_EVIDENCE,
    Stage1PaymentProvider.YOOKASSA: Stage1RefundProviderMode.PROVIDER_API_AFTER_EVIDENCE,
}

STAGE1_REFUND_DISPUTE_REQUIRED_EVIDENCE = (
    "order_id",
    "payment_attempt_id_or_payment_id",
    "provider",
    "provider_payment_reference",
    "amount_and_currency",
    "customer_reason_or_dispute_reason",
    "provider_status_snapshot",
    "finance_or_admin_actor",
    "support_ticket_or_audit_reference",
)

STAGE1_REFUND_DISPUTE_FORBIDDEN_OUTPUT_FIELDS = (
    "raw_provider_payload",
    "payment_url",
    "provider_secret",
    "api_key",
    "webhook_signature",
    "wallet_private_key",
    "full_crypto_address_if_not_required",
    "vpn_config_url",
)


def resolve_stage1_refund_dispute_admin_role(user: AdminUserModel) -> AdminRole:
    """Resolve an admin role with the same invalid-role behavior as other admin gates."""

    try:
        return AdminRole(user.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin role") from exc


def can_review_stage1_refund_dispute(role: AdminRole | str) -> bool:
    """Return whether a role may approve/refuse/reconcile refund and dispute state."""

    try:
        role_enum = AdminRole(role)
    except ValueError:
        return False
    return role_enum in STAGE1_REFUND_DISPUTE_REVIEW_ROLES


def can_intake_stage1_refund_dispute(role: AdminRole | str) -> bool:
    """Return whether a role may intake cases and escalate them to finance/admin."""

    try:
        role_enum = AdminRole(role)
    except ValueError:
        return False
    return role_enum in STAGE1_REFUND_DISPUTE_SUPPORT_INTAKE_ROLES


async def require_stage1_refund_dispute_reviewer(
    user: AdminUserModel = Depends(get_current_active_user),
) -> AdminUserModel:
    """FastAPI dependency for S1 refund/dispute financial state changes."""

    role = resolve_stage1_refund_dispute_admin_role(user)
    if settings.admin_2fa_required and not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin 2FA required")
    if role not in STAGE1_REFUND_DISPUTE_REVIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires finance or admin refund/dispute review role",
        )
    return user


def stage1_refund_provider_mode(provider: Stage1PaymentProvider | str) -> Stage1RefundProviderMode:
    """Resolve provider refund mode for S1 runbooks and provider readiness checks."""

    return STAGE1_REFUND_DISPUTE_PROVIDER_MODES[Stage1PaymentProvider(provider)]


def build_stage1_refund_dispute_runbook() -> dict[str, object]:
    """Serialize the S1 runbook contract for tests, evidence and internal diagnostics."""

    return {
        "actions": [action.value for action in Stage1RefundDisputeAction],
        "review_roles": sorted(role.value for role in STAGE1_REFUND_DISPUTE_REVIEW_ROLES),
        "support_intake_roles": sorted(role.value for role in STAGE1_REFUND_DISPUTE_SUPPORT_INTAKE_ROLES),
        "provider_modes": {
            provider.value: mode.value for provider, mode in STAGE1_REFUND_DISPUTE_PROVIDER_MODES.items()
        },
        "required_evidence": list(STAGE1_REFUND_DISPUTE_REQUIRED_EVIDENCE),
        "forbidden_output_fields": list(STAGE1_REFUND_DISPUTE_FORBIDDEN_OUTPUT_FIELDS),
        "sla": {
            "refund_support_ack": "<=1h for P1 payment/refund cases",
            "beta_support_first_response": "<=12h",
            "paid_but_no_access_or_orphan": "manual review queue; no unresolved case older than 24h",
        },
        "s1_provider_enablement_rule": (
            "Provider refund/dispute execution remains disabled until account, credential, webhook/status, "
            "idempotency, provider refund/support and reconciliation evidence exists."
        ),
    }


__all__ = [
    "STAGE1_REFUND_DISPUTE_FORBIDDEN_OUTPUT_FIELDS",
    "STAGE1_REFUND_DISPUTE_PROVIDER_MODES",
    "STAGE1_REFUND_DISPUTE_REQUIRED_EVIDENCE",
    "STAGE1_REFUND_DISPUTE_REVIEW_ROLES",
    "STAGE1_REFUND_DISPUTE_SUPPORT_INTAKE_ROLES",
    "Stage1RefundDisputeAction",
    "Stage1RefundProviderMode",
    "build_stage1_refund_dispute_runbook",
    "can_intake_stage1_refund_dispute",
    "can_review_stage1_refund_dispute",
    "require_stage1_refund_dispute_reviewer",
    "resolve_stage1_refund_dispute_admin_role",
    "stage1_refund_provider_mode",
]
