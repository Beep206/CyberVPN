"""Canonical partner workspace permissions."""

from enum import StrEnum


class PartnerPermission(StrEnum):
    WORKSPACE_READ = "workspace_read"
    OPERATIONS_WRITE = "operations_write"
    MEMBERSHIP_READ = "membership_read"
    MEMBERSHIP_WRITE = "membership_write"
    CODES_READ = "codes_read"
    CODES_WRITE = "codes_write"
    EARNINGS_READ = "earnings_read"
    PAYOUTS_READ = "payouts_read"
    PAYOUTS_WRITE = "payouts_write"
    TRAFFIC_READ = "traffic_read"
    TRAFFIC_WRITE = "traffic_write"
    INTEGRATIONS_READ = "integrations_read"
    INTEGRATIONS_WRITE = "integrations_write"
