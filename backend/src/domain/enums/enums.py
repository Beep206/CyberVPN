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
