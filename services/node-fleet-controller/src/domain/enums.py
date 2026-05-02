from __future__ import annotations

from enum import StrEnum


class RequestType(StrEnum):
    PROVISIONING = "provisioning"
    REPLACEMENT = "replacement"
    DRAIN = "drain"
    QUARANTINE = "quarantine"
    FAILOVER = "failover"


class RequestStatus(StrEnum):
    ACCEPTED = "accepted"
    BLOCKED_POLICY = "blocked_policy"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class OperationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class LifecycleState(StrEnum):
    REQUESTED = "requested"
    PLACEMENT_SELECTED = "placement_selected"
    PLAN_CREATED = "plan_created"
    PLAN_APPROVED = "plan_approved"
    APPLYING_INFRA = "applying_infra"
    VM_CREATED = "vm_created"
    BOOTSTRAP_ISSUED = "bootstrap_issued"
    BOOTING = "booting"
    ENROLLING = "enrolling"
    CONFIGURING = "configuring"
    VERIFYING = "verifying"
    READY = "ready"
    TRAFFIC_ELIGIBLE = "traffic_eligible"
    DRAINING = "draining"
    QUARANTINED = "quarantined"
    ROTATING = "rotating"
    TERMINATING = "terminating"
    DELETED = "deleted"
    FAILED = "failed"


class BootstrapState(StrEnum):
    NOT_ISSUED = "not_issued"
    ISSUED = "issued"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class EnrollmentStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFIGURED = "configured"
    REJECTED = "rejected"


class CertificateState(StrEnum):
    NOT_ISSUED = "not_issued"
    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"


class ProviderResourceState(StrEnum):
    PLANNED = "planned"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    DRIFTED = "drifted"
    TERMINATED = "terminated"


class OperationStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ComponentStatus(StrEnum):
    UNKNOWN = "unknown"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"


class SyntheticStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class HealthState(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class SignalSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AdapterAckState(StrEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"


class TrafficEligibilityState(StrEnum):
    BLOCKED = "blocked"
    READY = "ready"
    ELIGIBLE = "eligible"
