from src.domain.enums.enums import (
    AccessDeliveryChannelStatus,
    AccessDeliveryChannelType,
    AttributionTouchpointType,
    CommercialOwnerSource,
    CommercialOwnerType,
    CommissionabilityStatus,
    CreativeApprovalKind,
    CreativeApprovalStatus,
    CustomerCommercialBindingStatus,
    CustomerCommercialBindingType,
    DeviceCredentialStatus,
    DeviceCredentialType,
    DisputeCaseKind,
    DisputeCaseStatus,
    EarningEventStatus,
    EarningHoldReasonType,
    EarningHoldStatus,
    EntitlementGrantSourceType,
    EntitlementGrantStatus,
    GovernanceActionStatus,
    GovernanceActionType,
    GrowthRewardType,
    PartnerPayoutAccountApprovalStatus,
    PartnerPayoutAccountStatus,
    PartnerPayoutAccountVerificationStatus,
    PartnerStatementStatus,
    PaymentDisputeOutcomeClass,
    PaymentDisputeStatus,
    PaymentDisputeSubtype,
    PilotCohortStatus,
    PilotGateStatus,
    PilotGoNoGoStatus,
    PilotLaneKey,
    PilotOwnerAcknowledgementStatus,
    PilotOwnerTeam,
    PilotRollbackDrillStatus,
    PilotRollbackScopeClass,
    PilotRolloutWindowKind,
    PilotRolloutWindowStatus,
    PilotSurfaceKey,
    PolicyApprovalState,
    PolicyVersionStatus,
    ProvisioningProfileStatus,
    RefundStatus,
    ReserveReasonType,
    ReserveScope,
    ReserveStatus,
    RiskReviewDecision,
    RiskReviewStatus,
    ServiceIdentityStatus,
    SettlementPeriodStatus,
    StatementAdjustmentDirection,
    StatementAdjustmentType,
    SurfacePolicyCapability,
    TrafficDeclarationKind,
    TrafficDeclarationStatus,
)


def test_attribution_touchpoint_type_values_are_frozen() -> None:
    assert [member.value for member in AttributionTouchpointType] == [
        "explicit_code",
        "passive_click",
        "deep_link",
        "qr_scan",
        "storefront_origin",
        "campaign_params",
        "invite_redemption",
        "postback",
        "manual_support_action",
    ]


def test_commercial_owner_type_values_are_frozen() -> None:
    assert [member.value for member in CommercialOwnerType] == [
        "none",
        "affiliate",
        "performance",
        "reseller",
        "direct_store",
    ]


def test_commercial_owner_source_values_are_frozen() -> None:
    assert [member.value for member in CommercialOwnerSource] == [
        "explicit_code",
        "passive_click",
        "persistent_reseller_binding",
        "storefront_default",
        "manual_override",
        "contract_assignment",
    ]


def test_customer_commercial_binding_values_are_frozen() -> None:
    assert [member.value for member in CustomerCommercialBindingType] == [
        "reseller_binding",
        "storefront_default_owner",
        "manual_override",
        "contract_assignment",
    ]
    assert [member.value for member in CustomerCommercialBindingStatus] == [
        "active",
        "released",
        "superseded",
    ]


def test_growth_reward_type_values_are_frozen() -> None:
    assert [member.value for member in GrowthRewardType] == [
        "invite_reward",
        "referral_credit",
        "bonus_days",
        "gift_bonus",
    ]


def test_policy_lifecycle_values_are_frozen() -> None:
    assert [member.value for member in PolicyApprovalState] == [
        "draft",
        "approved",
        "rejected",
    ]
    assert [member.value for member in PolicyVersionStatus] == [
        "draft",
        "active",
        "superseded",
        "archived",
    ]


def test_payment_dispute_normalization_values_are_frozen() -> None:
    assert [member.value for member in PaymentDisputeSubtype] == [
        "inquiry",
        "warning",
        "chargeback",
        "dispute_reversal",
        "second_chargeback",
    ]
    assert [member.value for member in PaymentDisputeOutcomeClass] == [
        "open",
        "won",
        "lost",
        "reversed",
    ]
    assert [member.value for member in PaymentDisputeStatus] == [
        "opened",
        "evidence_required",
        "evidence_submitted",
        "under_review",
        "closed",
    ]


def test_refund_lifecycle_values_are_frozen() -> None:
    assert [member.value for member in RefundStatus] == [
        "requested",
        "processing",
        "succeeded",
        "failed",
        "cancelled",
    ]


def test_risk_workflow_values_are_frozen() -> None:
    assert [member.value for member in RiskReviewStatus] == [
        "open",
        "resolved",
        "dismissed",
    ]
    assert [member.value for member in RiskReviewDecision] == [
        "pending",
        "allow",
        "block",
        "monitor",
        "hold",
    ]
    assert [member.value for member in GovernanceActionType] == [
        "payout_freeze",
        "code_suspension",
        "reserve_extension",
        "traffic_probation",
        "creative_restriction",
        "manual_override",
    ]
    assert [member.value for member in GovernanceActionStatus] == [
        "requested",
        "applied",
        "cancelled",
    ]


def test_operational_overlay_values_are_frozen() -> None:
    assert [member.value for member in TrafficDeclarationKind] == [
        "approved_sources",
        "postback_readiness",
    ]
    assert [member.value for member in TrafficDeclarationStatus] == [
        "submitted",
        "action_required",
        "under_review",
        "complete",
        "blocked",
    ]
    assert [member.value for member in CreativeApprovalKind] == [
        "creative_approval",
    ]
    assert [member.value for member in CreativeApprovalStatus] == [
        "submitted",
        "action_required",
        "under_review",
        "complete",
        "blocked",
    ]
    assert [member.value for member in DisputeCaseKind] == [
        "payout_dispute",
        "chargeback_review",
        "evidence_collection",
        "reserve_review",
    ]
    assert [member.value for member in DisputeCaseStatus] == [
        "open",
        "waiting_on_partner",
        "waiting_on_ops",
        "resolved",
        "closed",
    ]


def test_pilot_control_values_are_frozen() -> None:
    assert [member.value for member in PilotLaneKey] == [
        "invite_gift",
        "consumer_referral",
        "creator_affiliate",
        "performance_media_buyer",
        "reseller_distribution",
    ]
    assert [member.value for member in PilotSurfaceKey] == [
        "official_web",
        "partner_storefront",
        "partner_portal",
        "miniapp",
        "telegram_bot",
        "desktop_client",
    ]
    assert [member.value for member in PilotCohortStatus] == [
        "scheduled",
        "active",
        "paused",
        "completed",
        "cancelled",
    ]
    assert [member.value for member in PilotRolloutWindowKind] == [
        "host",
        "partner_workspace",
        "channel",
    ]
    assert [member.value for member in PilotRolloutWindowStatus] == [
        "scheduled",
        "active",
        "paused",
        "closed",
    ]
    assert [member.value for member in PilotGateStatus] == [
        "green",
        "yellow",
        "red",
    ]
    assert [member.value for member in PilotOwnerTeam] == [
        "platform",
        "finance_ops",
        "risk_ops",
        "support",
        "partner_ops",
        "qa",
    ]
    assert [member.value for member in PilotOwnerAcknowledgementStatus] == [
        "acknowledged",
    ]
    assert [member.value for member in PilotRollbackScopeClass] == [
        "config_rollback",
        "traffic_rollback",
        "decision_path_rollback",
        "availability_rollback",
        "containment_mode",
    ]
    assert [member.value for member in PilotRollbackDrillStatus] == [
        "passed",
        "failed",
    ]
    assert [member.value for member in PilotGoNoGoStatus] == [
        "approved",
        "hold",
        "no_go",
    ]


def test_commissionability_lifecycle_values_are_frozen() -> None:
    assert [member.value for member in CommissionabilityStatus] == [
        "pending",
        "eligible",
        "ineligible",
    ]


def test_settlement_foundation_values_are_frozen() -> None:
    assert [member.value for member in EarningEventStatus] == [
        "on_hold",
        "available",
        "blocked",
        "reversed",
    ]
    assert [member.value for member in EarningHoldReasonType] == [
        "payout_hold",
        "risk_review",
        "manual",
        "reserve",
        "dispute",
    ]
    assert [member.value for member in EarningHoldStatus] == [
        "active",
        "released",
        "superseded",
        "expired",
    ]
    assert [member.value for member in ReserveScope] == [
        "partner_account",
        "earning_event",
    ]
    assert [member.value for member in ReserveReasonType] == [
        "risk_buffer",
        "dispute_buffer",
        "manual",
    ]
    assert [member.value for member in ReserveStatus] == [
        "active",
        "released",
    ]
    assert [member.value for member in SettlementPeriodStatus] == [
        "open",
        "closed",
    ]
    assert [member.value for member in PartnerStatementStatus] == [
        "open",
        "closed",
    ]
    assert [member.value for member in PartnerPayoutAccountStatus] == [
        "active",
        "suspended",
        "archived",
    ]
    assert [member.value for member in PartnerPayoutAccountVerificationStatus] == [
        "pending",
        "verified",
    ]
    assert [member.value for member in PartnerPayoutAccountApprovalStatus] == [
        "pending",
        "approved",
    ]
    assert [member.value for member in StatementAdjustmentType] == [
        "manual",
        "refund_clawback",
        "dispute_clawback",
        "reserve_application",
        "reserve_release",
    ]
    assert [member.value for member in StatementAdjustmentDirection] == [
        "credit",
        "debit",
    ]


def test_surface_policy_capabilities_are_frozen() -> None:
    assert [member.value for member in SurfacePolicyCapability] == [
        "external_code_override",
        "same_owner_only_codes",
        "promo_stacking",
        "wallet_spend",
        "invite_redemption",
        "referral_discount",
        "customer_facing",
        "operator_facing",
    ]


def test_service_access_foundation_values_are_frozen() -> None:
    assert [member.value for member in ServiceIdentityStatus] == [
        "active",
        "suspended",
        "revoked",
    ]
    assert [member.value for member in ProvisioningProfileStatus] == [
        "draft",
        "active",
        "archived",
    ]
    assert [member.value for member in EntitlementGrantStatus] == [
        "pending",
        "active",
        "suspended",
        "revoked",
        "expired",
    ]
    assert [member.value for member in EntitlementGrantSourceType] == [
        "order",
        "growth_reward",
        "renewal",
        "manual",
    ]
    assert [member.value for member in DeviceCredentialType] == [
        "mobile_device",
        "desktop_client",
        "telegram_bot",
        "subscription_token",
    ]
    assert [member.value for member in DeviceCredentialStatus] == [
        "active",
        "revoked",
        "expired",
    ]
    assert [member.value for member in AccessDeliveryChannelType] == [
        "subscription_url",
        "shared_client",
        "telegram_bot",
        "desktop_manifest",
    ]
    assert [member.value for member in AccessDeliveryChannelStatus] == [
        "active",
        "suspended",
        "archived",
    ]
