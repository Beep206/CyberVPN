"""Analytics and stats aggregation tasks."""

from src.tasks.analytics.daily_stats import aggregate_daily_stats
from src.tasks.analytics.financial_stats import aggregate_financial_stats

__all__ = ["aggregate_financial_stats", "aggregate_daily_stats"]
