"""Admin DTO models for telegram-bot service.

This module contains Pydantic models for admin statistics, analytics,
and system health monitoring.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class UserStatsDTO(BaseModel):
    """User statistics for admin dashboard.

    Attributes:
        total_users: Total registered users
        active_users: Users with active subscriptions
        expired_users: Users with expired subscriptions
        new_users_today: New registrations today
        new_users_week: New registrations this week
        new_users_month: New registrations this month
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_users: Annotated[int, Field(ge=0, description="Total users")]
    active_users: Annotated[int, Field(ge=0, description="Active subscription users")]
    expired_users: Annotated[int, Field(ge=0, description="Expired subscription users")]
    new_users_today: Annotated[int, Field(ge=0, description="New users today")]
    new_users_week: Annotated[int, Field(ge=0, description="New users this week")]
    new_users_month: Annotated[int, Field(ge=0, description="New users this month")]


class RevenueStatsDTO(BaseModel):
    """Revenue statistics for admin dashboard.

    Attributes:
        total_revenue: Total all-time revenue
        revenue_today: Revenue today
        revenue_week: Revenue this week
        revenue_month: Revenue this month
        revenue_by_gateway: Revenue breakdown by payment gateway
        revenue_by_plan: Revenue breakdown by subscription plan
        average_transaction: Average transaction value
        currency: Primary currency for reporting
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_revenue: Annotated[float, Field(ge=0, description="Total revenue")]
    revenue_today: Annotated[float, Field(ge=0, description="Revenue today")]
    revenue_week: Annotated[float, Field(ge=0, description="Revenue this week")]
    revenue_month: Annotated[float, Field(ge=0, description="Revenue this month")]
    revenue_by_gateway: dict[str, float] = Field(default_factory=dict, description="Revenue by gateway")
    revenue_by_plan: dict[str, float] = Field(default_factory=dict, description="Revenue by plan")
    average_transaction: Annotated[float, Field(ge=0, description="Average transaction value")]
    currency: str = Field(default="USD", description="Reporting currency")


class SubscriptionStatsDTO(BaseModel):
    """Subscription statistics for admin dashboard.

    Attributes:
        total_active: Total active subscriptions
        expiring_soon: Subscriptions expiring within 7 days
        expired_today: Subscriptions that expired today
        new_subscriptions_today: New subscriptions today
        new_subscriptions_week: New subscriptions this week
        new_subscriptions_month: New subscriptions this month
        by_plan: Subscription counts by plan
        renewal_rate: Renewal rate percentage
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_active: Annotated[int, Field(ge=0, description="Active subscriptions")]
    expiring_soon: Annotated[int, Field(ge=0, description="Expiring within 7 days")]
    expired_today: Annotated[int, Field(ge=0, description="Expired today")]
    new_subscriptions_today: Annotated[int, Field(ge=0, description="New subscriptions today")]
    new_subscriptions_week: Annotated[int, Field(ge=0, description="New subscriptions this week")]
    new_subscriptions_month: Annotated[int, Field(ge=0, description="New subscriptions this month")]
    by_plan: dict[str, int] = Field(default_factory=dict, description="Subscriptions by plan")
    renewal_rate: Annotated[float, Field(ge=0, le=100, description="Renewal rate %")]


class TrafficStatsDTO(BaseModel):
    """Traffic usage statistics for admin dashboard.

    Attributes:
        total_traffic_gb: Total traffic used (all time)
        traffic_today_gb: Traffic used today
        traffic_week_gb: Traffic used this week
        traffic_month_gb: Traffic used this month
        average_per_user_gb: Average traffic per user
        top_users: List of top traffic consumers (telegram_id, traffic_gb)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_traffic_gb: Annotated[float, Field(ge=0, description="Total traffic GB")]
    traffic_today_gb: Annotated[float, Field(ge=0, description="Traffic today GB")]
    traffic_week_gb: Annotated[float, Field(ge=0, description="Traffic this week GB")]
    traffic_month_gb: Annotated[float, Field(ge=0, description="Traffic this month GB")]
    average_per_user_gb: Annotated[float, Field(ge=0, description="Average per user GB")]
    top_users: list[tuple[int, float]] = Field(default_factory=list, description="Top users (telegram_id, traffic_gb)")


class ReferralStatsDTO(BaseModel):
    """Referral program statistics for admin dashboard.

    Attributes:
        total_referrals: Total referrals registered
        paid_referrals: Referrals who made payments
        conversion_rate: Referral-to-payment conversion rate
        total_rewards_given: Total rewards distributed
        rewards_by_type: Rewards breakdown by type
        top_referrers: Top referrers (telegram_id, referral_count)
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    total_referrals: Annotated[int, Field(ge=0, description="Total referrals")]
    paid_referrals: Annotated[int, Field(ge=0, description="Paid referrals")]
    conversion_rate: Annotated[float, Field(ge=0, le=100, description="Conversion rate %")]
    total_rewards_given: Annotated[int, Field(ge=0, description="Total rewards distributed")]
    rewards_by_type: dict[str, int] = Field(default_factory=dict, description="Rewards by type")
    top_referrers: list[tuple[int, int]] = Field(
        default_factory=list, description="Top referrers (telegram_id, count)"
    )


class SystemHealthDTO(BaseModel):
    """System health monitoring data.

    Attributes:
        status: Overall system status (healthy/degraded/down)
        uptime_seconds: System uptime in seconds
        api_response_time_ms: Backend API average response time
        database_status: Database connection status
        cache_status: Cache (Redis/Valkey) connection status
        bot_status: Telegram bot status
        active_connections: Number of active bot connections
        memory_usage_mb: Memory usage in MB
        cpu_usage_percent: CPU usage percentage
        last_check: Last health check timestamp
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    status: str = Field(..., description="System status (healthy/degraded/down)")
    uptime_seconds: Annotated[int, Field(ge=0, description="Uptime in seconds")]
    api_response_time_ms: Annotated[float, Field(ge=0, description="API response time ms")]
    database_status: str = Field(..., description="Database status")
    cache_status: str = Field(..., description="Cache status")
    bot_status: str = Field(..., description="Telegram bot status")
    active_connections: Annotated[int, Field(ge=0, description="Active connections")]
    memory_usage_mb: Annotated[float, Field(ge=0, description="Memory usage MB")]
    cpu_usage_percent: Annotated[float, Field(ge=0, le=100, description="CPU usage %")]
    last_check: datetime = Field(..., description="Last check timestamp")


class AdminStatsDTO(BaseModel):
    """Comprehensive admin statistics dashboard.

    Attributes:
        users: User statistics
        revenue: Revenue statistics
        subscriptions: Subscription statistics
        traffic: Traffic statistics
        referrals: Referral statistics
        system_health: System health data
        generated_at: Statistics generation timestamp
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    users: UserStatsDTO = Field(..., description="User statistics")
    revenue: RevenueStatsDTO = Field(..., description="Revenue statistics")
    subscriptions: SubscriptionStatsDTO = Field(..., description="Subscription statistics")
    traffic: TrafficStatsDTO = Field(..., description="Traffic statistics")
    referrals: ReferralStatsDTO = Field(..., description="Referral statistics")
    system_health: SystemHealthDTO = Field(..., description="System health")
    generated_at: datetime = Field(..., description="Statistics generation timestamp")
