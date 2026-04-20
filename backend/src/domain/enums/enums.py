from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    LIMITED = "limited"
    EXPIRED = "expired"


class ServerStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    MAINTENANCE = "maintenance"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(StrEnum):
    CRYPTOBOT = "cryptobot"
    YOOKASSA = "yookassa"
    STRIPE = "stripe"
    WALLET = "wallet"


class PaymentAttemptStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RefundStatus(StrEnum):
    REQUESTED = "requested"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommissionabilityStatus(StrEnum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class OutboxEventStatus(StrEnum):
    PENDING_PUBLICATION = "pending_publication"
    PARTIALLY_PUBLISHED = "partially_published"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxPublicationStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    SUBMITTED = "submitted"
    PUBLISHED = "published"
    FAILED = "failed"


class PartnerIntegrationCredentialKind(StrEnum):
    REPORTING_API_TOKEN = "reporting_api_token"  # noqa: S105
    POSTBACK_SECRET = "postback_secret"  # noqa: S105


class PartnerIntegrationCredentialStatus(StrEnum):
    READY = "ready"
    PENDING_ROTATION = "pending_rotation"
    BLOCKED = "blocked"


class PartnerIntegrationDeliveryChannel(StrEnum):
    REPORTING_EXPORT = "reporting_export"
    POSTBACK = "postback"


class PartnerIntegrationDeliveryStatus(StrEnum):
    DELIVERED = "delivered"
    FAILED = "failed"
    PAUSED = "paused"


class EarningEventStatus(StrEnum):
    ON_HOLD = "on_hold"
    AVAILABLE = "available"
    BLOCKED = "blocked"
    REVERSED = "reversed"


class EarningHoldReasonType(StrEnum):
    PAYOUT_HOLD = "payout_hold"
    RISK_REVIEW = "risk_review"
    MANUAL = "manual"
    RESERVE = "reserve"
    DISPUTE = "dispute"


class EarningHoldStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class ReserveScope(StrEnum):
    PARTNER_ACCOUNT = "partner_account"
    EARNING_EVENT = "earning_event"


class ReserveReasonType(StrEnum):
    RISK_BUFFER = "risk_buffer"
    DISPUTE_BUFFER = "dispute_buffer"
    MANUAL = "manual"


class ReserveStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"


class SettlementPeriodStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class PartnerStatementStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class StatementAdjustmentType(StrEnum):
    MANUAL = "manual"
    REFUND_CLAWBACK = "refund_clawback"
    DISPUTE_CLAWBACK = "dispute_clawback"
    RESERVE_APPLICATION = "reserve_application"
    RESERVE_RELEASE = "reserve_release"


class StatementAdjustmentDirection(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class PartnerPayoutAccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class PartnerPayoutAccountVerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"


class PartnerPayoutAccountApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"


class PayoutInstructionStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PayoutExecutionMode(StrEnum):
    DRY_RUN = "dry_run"
    LIVE = "live"


class PayoutExecutionStatus(StrEnum):
    REQUESTED = "requested"
    SUBMITTED = "submitted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECONCILED = "reconciled"
    CANCELLED = "cancelled"


class AdminRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"
    SUPPORT = "support"
    VIEWER = "viewer"


class PlanTier(StrEnum):
    BASIC = "basic"
    PRO = "pro"
    ULTRA = "ultra"
    CYBER = "cyber"


class PlanCode(StrEnum):
    START = "start"
    BASIC = "basic"
    PLUS = "plus"
    PRO = "pro"
    MAX = "max"
    TEST = "test"
    DEVELOPMENT = "development"


class CatalogVisibility(StrEnum):
    PUBLIC = "public"
    HIDDEN = "hidden"


class SaleChannel(StrEnum):
    WEB = "web"
    MINIAPP = "miniapp"
    TELEGRAM_BOT = "telegram_bot"
    ADMIN = "admin"


class SupportSLA(StrEnum):
    STANDARD = "standard"
    PRIORITY = "priority"
    VIP = "vip"
    INTERNAL = "internal"


class TemplateType(StrEnum):
    CLASH = "clash"
    HIDDIFY = "hiddify"
    OUTLINE = "outline"
    SING_BOX = "sing_box"
    V2RAY = "v2ray"


# --- Codes & Wallet system enums ---


class InviteSource(StrEnum):
    PURCHASE = "purchase"
    ADMIN_GRANT = "admin_grant"


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


class WalletTxType(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class WalletTxReason(StrEnum):
    REFERRAL_COMMISSION = "referral_commission"
    PARTNER_EARNING = "partner_earning"
    PARTNER_MARKUP = "partner_markup"
    ADMIN_TOPUP = "admin_topup"
    SUBSCRIPTION_PAYMENT = "subscription_payment"
    WITHDRAWAL = "withdrawal"
    WITHDRAWAL_FEE = "withdrawal_fee"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class WithdrawalStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WithdrawalMethod(StrEnum):
    CRYPTOBOT = "cryptobot"
    MANUAL = "manual"


class ReferralDurationMode(StrEnum):
    INDEFINITE = "indefinite"
    TIME_LIMITED = "time_limited"
    PAYMENT_COUNT = "payment_count"
    FIRST_PAYMENT_ONLY = "first_payment_only"


class CommercialOwnerType(StrEnum):
    NONE = "none"
    AFFILIATE = "affiliate"
    PERFORMANCE = "performance"
    RESELLER = "reseller"
    DIRECT_STORE = "direct_store"


class CommercialOwnerSource(StrEnum):
    EXPLICIT_CODE = "explicit_code"
    PASSIVE_CLICK = "passive_click"
    PERSISTENT_RESELLER_BINDING = "persistent_reseller_binding"
    STOREFRONT_DEFAULT = "storefront_default"
    MANUAL_OVERRIDE = "manual_override"
    CONTRACT_ASSIGNMENT = "contract_assignment"


class GrowthRewardType(StrEnum):
    INVITE_REWARD = "invite_reward"
    REFERRAL_CREDIT = "referral_credit"
    BONUS_DAYS = "bonus_days"
    GIFT_BONUS = "gift_bonus"


class GrowthRewardAllocationStatus(StrEnum):
    ALLOCATED = "allocated"
    REVERSED = "reversed"


class AttributionTouchpointType(StrEnum):
    EXPLICIT_CODE = "explicit_code"
    PASSIVE_CLICK = "passive_click"
    DEEP_LINK = "deep_link"
    QR_SCAN = "qr_scan"
    STOREFRONT_ORIGIN = "storefront_origin"
    CAMPAIGN_PARAMS = "campaign_params"
    INVITE_REDEMPTION = "invite_redemption"
    POSTBACK = "postback"
    MANUAL_SUPPORT_ACTION = "manual_support_action"


class CustomerCommercialBindingType(StrEnum):
    RESELLER_BINDING = "reseller_binding"
    STOREFRONT_DEFAULT_OWNER = "storefront_default_owner"
    MANUAL_OVERRIDE = "manual_override"
    CONTRACT_ASSIGNMENT = "contract_assignment"


class CustomerCommercialBindingStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"
    SUPERSEDED = "superseded"


class PolicyApprovalState(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class PolicyVersionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class PaymentDisputeSubtype(StrEnum):
    INQUIRY = "inquiry"
    WARNING = "warning"
    CHARGEBACK = "chargeback"
    DISPUTE_REVERSAL = "dispute_reversal"
    SECOND_CHARGEBACK = "second_chargeback"


class PaymentDisputeOutcomeClass(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    REVERSED = "reversed"


class PaymentDisputeStatus(StrEnum):
    OPENED = "opened"
    EVIDENCE_REQUIRED = "evidence_required"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    UNDER_REVIEW = "under_review"
    CLOSED = "closed"


class SurfacePolicyCapability(StrEnum):
    EXTERNAL_CODE_OVERRIDE = "external_code_override"
    SAME_OWNER_ONLY_CODES = "same_owner_only_codes"
    PROMO_STACKING = "promo_stacking"
    WALLET_SPEND = "wallet_spend"
    INVITE_REDEMPTION = "invite_redemption"
    REFERRAL_DISCOUNT = "referral_discount"
    CUSTOMER_FACING = "customer_facing"
    OPERATOR_FACING = "operator_facing"


class RealmType(StrEnum):
    CUSTOMER = "customer"
    PARTNER = "partner"
    ADMIN = "admin"
    SERVICE = "service"


class PrincipalClass(StrEnum):
    CUSTOMER = "customer"
    PARTNER_OPERATOR = "partner_operator"
    ADMIN = "admin"
    SERVICE = "service"


class PartnerAccountStatus(StrEnum):
    DRAFT = "draft"
    EMAIL_VERIFIED = "email_verified"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    NEEDS_INFO = "needs_info"
    WAITLISTED = "waitlisted"
    APPROVED_PROBATION = "approved_probation"
    ACTIVE = "active"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    TERMINATED = "terminated"
    DISABLED = "disabled"


class PartnerMembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class RiskIdentifierType(StrEnum):
    EMAIL = "email"
    DEVICE_ID = "device_id"
    TELEGRAM_ID = "telegram_id"
    PAYMENT_FINGERPRINT = "payment_fingerprint"
    IP_ADDRESS = "ip_address"


class RiskLinkType(StrEnum):
    SHARED_EMAIL = "shared_email"
    SHARED_DEVICE_ID = "shared_device_id"
    SHARED_TELEGRAM_ID = "shared_telegram_id"
    SHARED_PAYMENT_FINGERPRINT = "shared_payment_fingerprint"
    SHARED_IP_ADDRESS = "shared_ip_address"
    SHARED_IDENTIFIER = "shared_identifier"


class RiskReviewStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class RiskReviewDecision(StrEnum):
    PENDING = "pending"
    ALLOW = "allow"
    BLOCK = "block"
    MONITOR = "monitor"
    HOLD = "hold"


class GovernanceActionType(StrEnum):
    PAYOUT_FREEZE = "payout_freeze"
    CODE_SUSPENSION = "code_suspension"
    RESERVE_EXTENSION = "reserve_extension"
    TRAFFIC_PROBATION = "traffic_probation"
    CREATIVE_RESTRICTION = "creative_restriction"
    MANUAL_OVERRIDE = "manual_override"


class GovernanceActionStatus(StrEnum):
    REQUESTED = "requested"
    APPLIED = "applied"
    CANCELLED = "cancelled"


class TrafficDeclarationKind(StrEnum):
    APPROVED_SOURCES = "approved_sources"
    POSTBACK_READINESS = "postback_readiness"


class TrafficDeclarationStatus(StrEnum):
    SUBMITTED = "submitted"
    ACTION_REQUIRED = "action_required"
    UNDER_REVIEW = "under_review"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class CreativeApprovalKind(StrEnum):
    CREATIVE_APPROVAL = "creative_approval"


class CreativeApprovalStatus(StrEnum):
    SUBMITTED = "submitted"
    ACTION_REQUIRED = "action_required"
    UNDER_REVIEW = "under_review"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class DisputeCaseKind(StrEnum):
    PAYOUT_DISPUTE = "payout_dispute"
    CHARGEBACK_REVIEW = "chargeback_review"
    EVIDENCE_COLLECTION = "evidence_collection"
    RESERVE_REVIEW = "reserve_review"


class DisputeCaseStatus(StrEnum):
    OPEN = "open"
    WAITING_ON_PARTNER = "waiting_on_partner"
    WAITING_ON_OPS = "waiting_on_ops"
    RESOLVED = "resolved"
    CLOSED = "closed"


class PilotLaneKey(StrEnum):
    INVITE_GIFT = "invite_gift"
    CONSUMER_REFERRAL = "consumer_referral"
    CREATOR_AFFILIATE = "creator_affiliate"
    PERFORMANCE_MEDIA_BUYER = "performance_media_buyer"
    RESELLER_DISTRIBUTION = "reseller_distribution"


class PilotSurfaceKey(StrEnum):
    OFFICIAL_WEB = "official_web"
    PARTNER_STOREFRONT = "partner_storefront"
    PARTNER_PORTAL = "partner_portal"
    MINIAPP = "miniapp"
    TELEGRAM_BOT = "telegram_bot"
    DESKTOP_CLIENT = "desktop_client"


class PilotGateStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class PilotCohortStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PilotRolloutWindowKind(StrEnum):
    HOST = "host"
    PARTNER_WORKSPACE = "partner_workspace"
    CHANNEL = "channel"


class PilotRolloutWindowStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class PilotOwnerTeam(StrEnum):
    PLATFORM = "platform"
    FINANCE_OPS = "finance_ops"
    RISK_OPS = "risk_ops"
    SUPPORT = "support"
    PARTNER_OPS = "partner_ops"
    QA = "qa"


class PilotOwnerAcknowledgementStatus(StrEnum):
    ACKNOWLEDGED = "acknowledged"


class PilotRollbackScopeClass(StrEnum):
    CONFIG_ROLLBACK = "config_rollback"
    TRAFFIC_ROLLBACK = "traffic_rollback"
    DECISION_PATH_ROLLBACK = "decision_path_rollback"
    AVAILABILITY_ROLLBACK = "availability_rollback"
    CONTAINMENT_MODE = "containment_mode"


class PilotRollbackDrillStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class PilotGoNoGoStatus(StrEnum):
    APPROVED = "approved"
    HOLD = "hold"
    NO_GO = "no_go"


class ServiceIdentityStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class ProvisioningProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class EntitlementGrantStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class EntitlementGrantSourceType(StrEnum):
    ORDER = "order"
    GROWTH_REWARD = "growth_reward"
    RENEWAL = "renewal"
    MANUAL = "manual"


class DeviceCredentialType(StrEnum):
    MOBILE_DEVICE = "mobile_device"
    DESKTOP_CLIENT = "desktop_client"
    TELEGRAM_BOT = "telegram_bot"
    SUBSCRIPTION_TOKEN = "subscription_token"  # noqa: S105


class DeviceCredentialStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AccessDeliveryChannelType(StrEnum):
    SUBSCRIPTION_URL = "subscription_url"
    SHARED_CLIENT = "shared_client"
    TELEGRAM_BOT = "telegram_bot"
    DESKTOP_MANIFEST = "desktop_manifest"


class AccessDeliveryChannelStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
