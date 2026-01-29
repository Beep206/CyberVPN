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
