"""Pydantic DTO models for telegram-bot service.

This package contains all data transfer objects (DTOs) used for communication
with the Backend API and internal data structures.
"""

from __future__ import annotations

# Admin models
from .admin import (
    AdminStatsDTO,
    ReferralStatsDTO,
    RevenueStatsDTO,
    SubscriptionStatsDTO,
    SystemHealthDTO,
    TrafficStatsDTO,
    UserStatsDTO,
)

# Broadcast models
from .broadcast import (
    BroadcastAudience,
    BroadcastButton,
    BroadcastDTO,
    BroadcastStats,
    BroadcastStatus,
)

# Notification models
from .notification import (
    NotificationDTO,
    NotificationPriority,
    NotificationStats,
    NotificationType,
)

# Payment models
from .payment import InvoiceDTO, PaymentDTO, PaymentGateway, PaymentStatus

# Promocode models
from .promocode import PromocodeActivation, PromocodeDTO, PromocodeType

# Referral models
from .referral import (
    ReferralDTO,
    ReferralReward,
    ReferralStats,
    ReferralUser,
    RewardForm,
    RewardStrategy,
    RewardType,
)

# Subscription models
from .subscription import (
    Discount,
    PlanAvailability,
    PlanDuration,
    PlanType,
    PurchaseContext,
    ResetStrategy,
    SubscriptionPlan,
)

# User models
from .user import UserDTO, UserProfile, UserStatus

__all__ = [
    # Admin
    "AdminStatsDTO",
    # Broadcast
    "BroadcastAudience",
    "BroadcastButton",
    "BroadcastDTO",
    "BroadcastStats",
    "BroadcastStatus",
    # Subscription
    "Discount",
    # Payment
    "InvoiceDTO",
    # Notification
    "NotificationDTO",
    "NotificationPriority",
    "NotificationStats",
    "NotificationType",
    "PaymentDTO",
    "PaymentGateway",
    "PaymentStatus",
    "PlanAvailability",
    "PlanDuration",
    "PlanType",
    # Promocode
    "PromocodeActivation",
    "PromocodeDTO",
    "PromocodeType",
    "PurchaseContext",
    # Referral
    "ReferralDTO",
    "ReferralReward",
    "ReferralStats",
    "ReferralStatsDTO",
    "ReferralUser",
    "ResetStrategy",
    "RevenueStatsDTO",
    "RewardForm",
    "RewardStrategy",
    "RewardType",
    "SubscriptionPlan",
    "SubscriptionStatsDTO",
    "SystemHealthDTO",
    "TrafficStatsDTO",
    # User
    "UserDTO",
    "UserProfile",
    "UserStatsDTO",
    "UserStatus",
]
