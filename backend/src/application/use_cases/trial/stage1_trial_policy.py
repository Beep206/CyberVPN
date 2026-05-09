"""Canonical Stage 1 trial policy."""

from __future__ import annotations

from dataclasses import dataclass

STAGE1_TRIAL_DURATION_DAYS = 3
STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
STAGE1_TRIAL_DEVICE_LIMIT = 1
STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY = "NO_RESET"
STAGE1_TRIAL_ONE_PER_ACCOUNT = True
STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_MAX = 3
STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_WINDOW_SECONDS = 3600


@dataclass(frozen=True, slots=True)
class Stage1TrialPolicy:
    """Public and provisioning-facing S1 trial policy values."""

    duration_days: int = STAGE1_TRIAL_DURATION_DAYS
    device_limit: int = STAGE1_TRIAL_DEVICE_LIMIT
    traffic_limit_bytes: int = STAGE1_TRIAL_TRAFFIC_LIMIT_BYTES
    traffic_limit_strategy: str = STAGE1_TRIAL_TRAFFIC_LIMIT_STRATEGY
    one_trial_per_account: bool = STAGE1_TRIAL_ONE_PER_ACCOUNT
    activation_rate_limit_max: int = STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_MAX
    activation_rate_limit_window_seconds: int = STAGE1_TRIAL_ACTIVATE_RATE_LIMIT_WINDOW_SECONDS


def get_stage1_trial_policy() -> Stage1TrialPolicy:
    """Return the immutable S1 trial policy used by API and provisioning code."""

    return Stage1TrialPolicy()
