"""Framework-independent VPN Tester value constants."""

from enum import StrEnum


class VpnTesterMode(StrEnum):
    CONTRACT = "contract"
    RUNTIME = "runtime"
    ALL_TARIFFS = "all_tariffs"
    BALANCER_PREVIEW = "balancer_preview"


class VpnTesterRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASS = "pass"  # noqa: S105 - test status value, not a credential.
    FAIL = "fail"
    DEGRADED = "degraded"
    CANCELLED = "cancelled"


VPN_TESTER_RUN_STATUSES = tuple(status.value for status in VpnTesterRunStatus)
VPN_TESTER_RESULT_STATUSES = ("pass", "fail", "degraded", "skipped")
