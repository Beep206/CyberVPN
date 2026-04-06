from datetime import datetime
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.config.settings import settings


class AdapterBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class HelixAdapterManifestUnavailableError(RuntimeError):
    """Raised when the adapter refuses to issue a Helix manifest."""


class AdapterSupportedTransportProfile(AdapterBaseModel):
    profile_family: str
    min_transport_profile_version: int
    max_transport_profile_version: int
    supported_policy_versions: list[int]


class AdapterResolveManifestRequest(AdapterBaseModel):
    user_id: str
    desktop_client_id: str
    entitlement_id: str
    trace_id: str
    channel: str | None = None
    supported_protocol_versions: list[int] | None = None
    supported_transport_profiles: list[AdapterSupportedTransportProfile] | None = None
    preferred_fallback_core: str | None = None


class AdapterManifestSubject(AdapterBaseModel):
    user_id: str
    desktop_client_id: str
    entitlement_id: str
    channel: str


class AdapterManifestTransport(AdapterBaseModel):
    transport_family: str
    protocol_version: int
    session_mode: str


class AdapterManifestTransportProfile(AdapterBaseModel):
    transport_profile_id: str
    profile_family: str
    profile_version: int
    policy_version: int
    deprecation_state: str


class AdapterManifestCompatibilityWindow(AdapterBaseModel):
    profile_family: str
    min_transport_profile_version: int
    max_transport_profile_version: int


class AdapterManifestHealthPolicy(AdapterBaseModel):
    startup_timeout_seconds: int
    runtime_unhealthy_threshold: int


class AdapterManifestCapabilityProfile(AdapterBaseModel):
    required_capabilities: list[str]
    fallback_core: str
    health_policy: AdapterManifestHealthPolicy


class AdapterManifestRoute(AdapterBaseModel):
    endpoint_ref: str
    preference: int
    policy_tag: str


class AdapterManifestCredentials(AdapterBaseModel):
    key_id: str
    token: str


class AdapterSignature(AdapterBaseModel):
    alg: str
    key_id: str
    sig: str


class AdapterManifestIntegrity(AdapterBaseModel):
    manifest_hash: str
    signature: AdapterSignature


class AdapterManifestObservability(AdapterBaseModel):
    trace_id: str
    metrics_namespace: str


class AdapterManifestDocument(AdapterBaseModel):
    schema_version: str
    manifest_id: str
    rollout_id: str
    issued_at: datetime
    expires_at: datetime
    subject: AdapterManifestSubject
    transport: AdapterManifestTransport
    transport_profile: AdapterManifestTransportProfile
    compatibility_window: AdapterManifestCompatibilityWindow
    capability_profile: AdapterManifestCapabilityProfile
    routes: list[AdapterManifestRoute]
    credentials: AdapterManifestCredentials
    integrity: AdapterManifestIntegrity
    observability: AdapterManifestObservability


class AdapterResolveManifestResponse(AdapterBaseModel):
    manifest_version_id: str
    manifest: AdapterManifestDocument
    selected_profile_policy: "AdapterTransportProfilePolicySummary | None" = None


class AdapterClientCapabilityDefaults(AdapterBaseModel):
    schema_version: str
    client_family: str
    default_channel: str
    supported_protocol_versions: list[int]
    supported_transport_profiles: list[AdapterSupportedTransportProfile]
    required_capabilities: list[str]
    fallback_cores: list[str]
    rollout_channels: list[str]


class AdapterNodeRegistryRecord(AdapterBaseModel):
    service_node_id: str
    remnawave_node_id: str
    node_name: str
    hostname: str | None = None
    transport_enabled: bool
    rollout_channel: str
    node_group: str
    adapter_node_label: str
    last_heartbeat_at: datetime | None = None
    daemon_version: str | None = None
    active_rollout_id: str | None = None
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime


class AdapterRolloutBatchRecord(AdapterBaseModel):
    rollout_id: str
    channel: str
    desired_state: str
    batch_id: str
    manifest_version: str
    target_nodes: int
    completed_nodes: int
    failed_nodes: int
    desktop_connect_success_rate: float
    desktop_fallback_rate: float
    pause_on_rollback_spike: bool
    revoke_on_manifest_error: bool
    published_at: datetime
    created_at: datetime
    updated_at: datetime


class AdapterRolloutBatchSummary(AdapterBaseModel):
    batch_id: str
    manifest_version: str
    target_nodes: int
    completed_nodes: int
    failed_nodes: int


class AdapterRolloutNodeSummary(AdapterBaseModel):
    healthy: int
    stale: int
    rolled_back: int


class AdapterRolloutDesktopSummary(AdapterBaseModel):
    connect_success_rate: float
    fallback_rate: float
    continuity_observed_events: int = 0
    continuity_success_rate: float = 0.0
    cross_route_recovery_rate: float = 0.0
    benchmark_observed_events: int = 0
    throughput_evidence_observed_events: int = 0
    average_benchmark_throughput_kbps: float | None = None
    average_relative_throughput_ratio: float | None = None
    average_relative_open_to_first_byte_gap_ratio: float | None = None


class AdapterTransportProfilePolicySummary(AdapterBaseModel):
    observed_events: int
    connect_success_rate: float
    fallback_rate: float
    continuity_success_rate: float
    cross_route_recovery_rate: float
    policy_score: int
    degraded: bool
    advisory_state: str = "healthy"
    recommended_action: str | None = None
    selection_eligible: bool = True
    new_session_issuable: bool = True
    new_session_posture: str = "preferred"
    suppression_window_active: bool = False
    suppression_reason: str | None = None
    suppression_observation_count: int = 0
    suppressed_until: datetime | None = None


class AdapterRolloutPolicySummary(AdapterBaseModel):
    pause_on_rollback_spike: bool
    revoke_on_manifest_error: bool
    active_transport_profile_id: str | None = None
    active_profile_policy: AdapterTransportProfilePolicySummary | None = None
    recommended_transport_profile_id: str | None = None
    healthy_candidate_count: int = 0
    eligible_candidate_count: int = 0
    suppressed_candidate_count: int = 0
    active_profile_suppressed: bool = False
    channel_posture: str = "healthy"
    automatic_reaction: str = "none"
    applied_automatic_reaction: str | None = None
    applied_transport_profile_id: str | None = None
    automatic_reaction_trigger_reason: str | None = None
    automatic_reaction_updated_at: datetime | None = None
    pause_recommended: bool = False
    profile_rotation_recommended: bool = False
    recommended_action: str | None = None


class AdapterRolloutStateResponse(AdapterBaseModel):
    schema_version: str
    rollout_id: str
    channel: str
    desired_state: str
    published_at: datetime
    current_batch: AdapterRolloutBatchSummary
    nodes: AdapterRolloutNodeSummary
    desktop: AdapterRolloutDesktopSummary
    policy: AdapterRolloutPolicySummary


class AdapterRolloutCanaryThresholdSummary(AdapterBaseModel):
    min_connect_success_rate: float
    max_fallback_rate: float
    min_continuity_observations: int
    require_throughput_evidence: bool
    min_relative_throughput_ratio: float
    max_relative_open_to_first_byte_gap_ratio: float
    min_continuity_success_rate: float
    min_cross_route_recovery_rate: float


class AdapterRolloutCanarySnapshotSummary(AdapterBaseModel):
    desired_state: str
    failed_nodes: int
    rolled_back_nodes: int
    connect_success_rate: float
    fallback_rate: float
    continuity_observed_events: int
    continuity_success_rate: float
    cross_route_recovery_rate: float
    benchmark_observed_events: int = 0
    throughput_evidence_observed_events: int = 0
    average_benchmark_throughput_kbps: float | None = None
    average_relative_throughput_ratio: float | None = None
    average_relative_open_to_first_byte_gap_ratio: float | None = None
    channel_posture: str
    active_profile_advisory_state: str | None = None
    active_profile_new_session_posture: str | None = None
    applied_automatic_reaction: str | None = None
    applied_transport_profile_id: str | None = None


class AdapterRolloutCanaryEvidenceResponse(AdapterBaseModel):
    schema_version: str
    rollout_id: str
    channel: str
    evaluated_at: datetime
    decision: str
    reasons: list[str] = []
    evidence_gaps: list[str] = []
    recommended_follow_up_action: str | None = None
    recommended_follow_up_severity: str | None = None
    recommended_follow_up_tasks: list[str] = []
    thresholds: AdapterRolloutCanaryThresholdSummary
    snapshot: AdapterRolloutCanarySnapshotSummary


class AdapterTransportProfileRecord(AdapterBaseModel):
    transport_profile_id: str
    channel: str
    profile_family: str
    profile_version: int
    policy_version: int
    protocol_version: int
    session_mode: str
    status: str
    fallback_core: str
    required_capabilities: list[str]
    compatibility_min_profile_version: int
    compatibility_max_profile_version: int
    startup_timeout_seconds: int
    runtime_unhealthy_threshold: int
    policy: AdapterTransportProfilePolicySummary | None = None
    created_at: datetime
    updated_at: datetime


class AdapterPublishRolloutRequest(AdapterBaseModel):
    rollout_id: str
    batch_id: str
    channel: str
    manifest_version: str
    target_node_ids: list[str]
    pause_on_rollback_spike: bool = True
    revoke_on_manifest_error: bool = True


class AdapterManifestVersionRecord(AdapterBaseModel):
    manifest_version_id: str
    manifest_id: str
    rollout_id: str
    manifest_template_version: str
    transport_profile_id: str | None = None
    profile_family: str | None = None
    profile_version: int | None = None
    policy_version: int | None = None
    subject_user_id: str
    desktop_client_id: str
    entitlement_id: str
    channel: str
    protocol_version: int
    manifest_hash: str
    signature_alg: str
    signature_key_id: str
    signature: str
    revoked_at: datetime | None = None
    created_at: datetime


class AdapterNodeAssignmentCompatibilityWindow(AdapterBaseModel):
    min_transport_profile_version: int
    max_transport_profile_version: int


class AdapterNodeAssignmentTransportProfile(AdapterBaseModel):
    transport_profile_id: str
    profile_family: str
    profile_version: int
    policy_version: int
    compatibility_window: AdapterNodeAssignmentCompatibilityWindow


class AdapterNodeRuntimeProfile(AdapterBaseModel):
    bundle_version: str
    min_daemon_version: str
    ports: list[int]
    health_check_interval_seconds: int


class AdapterNodeRecovery(AdapterBaseModel):
    last_known_good_bundle: str
    rollback_timeout_seconds: int


class AdapterNodeAssignmentIntegrity(AdapterBaseModel):
    assignment_hash: str
    signature: AdapterSignature


class AdapterNodeAssignmentResponse(AdapterBaseModel):
    schema_version: str
    assignment_id: str
    rollout_id: str
    node_id: str
    channel: str
    issued_at: datetime
    expires_at: datetime
    desired_state: str
    transport_profile: AdapterNodeAssignmentTransportProfile
    runtime_profile: AdapterNodeRuntimeProfile
    recovery: AdapterNodeRecovery
    integrity: AdapterNodeAssignmentIntegrity


class AdapterRuntimeEvidenceModel(AdapterBaseModel):
    model_config = ConfigDict(extra="allow")


class AdapterDesktopRuntimeEventRecoveryEvidence(AdapterRuntimeEvidenceModel):
    same_route_recovered: bool | None = None
    ready_recovery_latency_ms: int | None = Field(default=None, ge=0)
    proxy_ready_latency_ms: int | None = Field(default=None, ge=0)
    proxy_ready_open_to_first_byte_gap_ms: int | None = Field(default=None, ge=0)
    successful_cross_route_recovers: int | None = Field(default=None, ge=0)
    last_cross_route_recovery_ms: int | None = Field(default=None, ge=0)


class AdapterDesktopRuntimeEventContinuityEvidence(AdapterRuntimeEvidenceModel):
    active_streams: int | None = Field(default=None, ge=0)
    pending_open_streams: int | None = Field(default=None, ge=0)
    continuity_grace_active: bool | None = None
    continuity_grace_route_endpoint_ref: str | None = None
    continuity_grace_remaining_ms: int | None = Field(default=None, ge=0)
    continuity_grace_entries: int | None = Field(default=None, ge=0)
    successful_continuity_recovers: int | None = Field(default=None, ge=0)
    failed_continuity_recovers: int | None = Field(default=None, ge=0)
    last_continuity_recovery_ms: int | None = Field(default=None, ge=0)
    successful_cross_route_recovers: int | None = Field(default=None, ge=0)
    last_cross_route_recovery_ms: int | None = Field(default=None, ge=0)
    active_route_quarantined: bool | None = None
    active_route_quarantine_remaining_ms: int | None = Field(default=None, ge=0)
    active_route_endpoint_ref: str | None = None
    active_route_score: int | None = None


class AdapterDesktopRuntimeEventBenchmarkEvidence(AdapterRuntimeEvidenceModel):
    benchmark_kind: str | None = None
    baseline_core: str | None = None
    target_count: int | None = Field(default=None, ge=0)
    successful_targets: int | None = Field(default=None, ge=0)
    attempts: int | None = Field(default=None, ge=0)
    successes: int | None = Field(default=None, ge=0)
    failures: int | None = Field(default=None, ge=0)
    throughput_kbps: float | None = Field(default=None, ge=0)
    relative_throughput_ratio_vs_baseline: float | None = Field(default=None, ge=0)
    median_connect_latency_ms: int | None = Field(default=None, ge=0)
    median_first_byte_latency_ms: int | None = Field(default=None, ge=0)
    median_open_to_first_byte_gap_ms: int | None = Field(default=None, ge=0)
    p95_open_to_first_byte_gap_ms: int | None = Field(default=None, ge=0)
    relative_open_to_first_byte_gap_ratio_vs_baseline: float | None = Field(
        default=None, ge=0
    )
    frame_queue_peak: int | None = Field(default=None, ge=0)
    recent_rtt_p95_ms: int | None = Field(default=None, ge=0)
    active_streams: int | None = Field(default=None, ge=0)
    pending_open_streams: int | None = Field(default=None, ge=0)


class AdapterDesktopRuntimeEventPayload(AdapterRuntimeEvidenceModel):
    stage: str | None = None
    runtime: str | None = None
    requested_core: str | None = None
    status: str | None = None
    proxy_url: str | None = None
    reason_code: str | None = None
    recovery: AdapterDesktopRuntimeEventRecoveryEvidence | None = None
    continuity: AdapterDesktopRuntimeEventContinuityEvidence | None = None
    benchmark: AdapterDesktopRuntimeEventBenchmarkEvidence | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_runtime_evidence(cls, value: Any) -> Any:
        if value is None:
            return {}
        if not isinstance(value, dict):
            return value

        data = dict(value)
        recovery_keys = {
            "same_route_recovered",
            "ready_recovery_latency_ms",
            "proxy_ready_latency_ms",
            "proxy_ready_open_to_first_byte_gap_ms",
            "successful_cross_route_recovers",
            "last_cross_route_recovery_ms",
        }
        continuity_keys = {
            "active_streams",
            "pending_open_streams",
            "continuity_grace_active",
            "continuity_grace_route_endpoint_ref",
            "continuity_grace_remaining_ms",
            "continuity_grace_entries",
            "successful_continuity_recovers",
            "failed_continuity_recovers",
            "last_continuity_recovery_ms",
            "successful_cross_route_recovers",
            "last_cross_route_recovery_ms",
            "active_route_quarantined",
            "active_route_quarantine_remaining_ms",
            "active_route_endpoint_ref",
            "active_route_score",
        }
        benchmark_keys = {
            "benchmark_kind",
            "baseline_core",
            "target_count",
            "successful_targets",
            "attempts",
            "successes",
            "failures",
            "throughput_kbps",
            "relative_throughput_ratio_vs_baseline",
            "median_connect_latency_ms",
            "median_first_byte_latency_ms",
            "median_open_to_first_byte_gap_ms",
            "p95_open_to_first_byte_gap_ms",
            "relative_open_to_first_byte_gap_ratio_vs_baseline",
            "frame_queue_peak",
            "recent_rtt_p95_ms",
            "active_streams",
            "pending_open_streams",
        }

        if "recovery" not in data:
            recovery = {
                key: data.pop(key)
                for key in list(recovery_keys)
                if key in data and data.get(key) is not None
            }
            if recovery:
                data["recovery"] = recovery

        if "continuity" not in data:
            continuity = {
                key: data.pop(key)
                for key in list(continuity_keys)
                if key in data and data.get(key) is not None
            }
            if continuity:
                data["continuity"] = continuity

        if "benchmark" not in data:
            benchmark = {
                key: data.pop(key)
                for key in list(benchmark_keys)
                if key in data and data.get(key) is not None
            }
            if benchmark:
                data["benchmark"] = benchmark

        return data


class AdapterDesktopRuntimeEventRequest(AdapterBaseModel):
    schema_version: str = "1.0"
    event_id: str
    user_id: str
    desktop_client_id: str
    manifest_version_id: str
    rollout_id: str
    transport_profile_id: str
    event_kind: str
    active_core: str
    fallback_core: str | None = None
    latency_ms: int | None = None
    route_count: int | None = None
    reason: str | None = None
    observed_at: datetime
    payload: AdapterDesktopRuntimeEventPayload = Field(
        default_factory=AdapterDesktopRuntimeEventPayload
    )


class AdapterDesktopRuntimeEventAck(AdapterBaseModel):
    status: str
    rollout_id: str
    event_kind: str


class HelixAdapterClient:
    DEFAULT_TIMEOUT: ClassVar[float] = 15.0

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or settings.helix_adapter_url).rstrip(
            "/"
        )
        self._token = (
            token or settings.helix_adapter_token.get_secret_value()
        )
        self._timeout = timeout
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"x-internal-token": self._token},
                transport=self._transport,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        client = await self._get_client()
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def resolve_manifest(
        self,
        request: AdapterResolveManifestRequest,
    ) -> AdapterResolveManifestResponse:
        try:
            data = await self._request(
                "POST",
                "/internal/manifests/resolve",
                json=request.model_dump(exclude_none=True),
            )
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise HelixAdapterManifestUnavailableError(
                    "Helix adapter did not issue a manifest for this desktop session"
                ) from error
            raise
        return AdapterResolveManifestResponse.model_validate(data)

    async def get_client_capability_defaults(self) -> AdapterClientCapabilityDefaults:
        data = await self._request("GET", "/internal/client-capabilities/defaults")
        return AdapterClientCapabilityDefaults.model_validate(data)

    async def list_nodes(self) -> list[AdapterNodeRegistryRecord]:
        data = await self._request("GET", "/admin/nodes")
        return [AdapterNodeRegistryRecord.model_validate(item) for item in data]

    async def get_rollout_status(self, rollout_id: str) -> AdapterRolloutStateResponse:
        data = await self._request("GET", f"/internal/rollouts/{rollout_id}/status")
        return AdapterRolloutStateResponse.model_validate(data)

    async def get_rollout_canary_evidence(
        self, rollout_id: str
    ) -> AdapterRolloutCanaryEvidenceResponse:
        data = await self._request(
            "GET", f"/internal/rollouts/{rollout_id}/canary-evidence"
        )
        return AdapterRolloutCanaryEvidenceResponse.model_validate(data)

    async def list_transport_profiles(self) -> list[AdapterTransportProfileRecord]:
        data = await self._request("GET", "/admin/transport-profiles")
        return [AdapterTransportProfileRecord.model_validate(item) for item in data]

    async def publish_rollout(
        self,
        request: AdapterPublishRolloutRequest,
    ) -> AdapterRolloutBatchRecord:
        data = await self._request(
            "POST",
            "/admin/rollouts",
            json=request.model_dump(),
        )
        return AdapterRolloutBatchRecord.model_validate(data)

    async def pause_rollout(self, rollout_id: str) -> AdapterRolloutBatchRecord:
        data = await self._request("POST", f"/admin/rollouts/{rollout_id}/pause")
        return AdapterRolloutBatchRecord.model_validate(data)

    async def revoke_manifest(
        self, manifest_version_id: str
    ) -> AdapterManifestVersionRecord:
        data = await self._request(
            "POST", f"/admin/manifests/{manifest_version_id}/revoke"
        )
        return AdapterManifestVersionRecord.model_validate(data)

    async def resolve_node_assignment(
        self, node_id: str
    ) -> AdapterNodeAssignmentResponse:
        data = await self._request("GET", f"/internal/nodes/{node_id}/assignment")
        return AdapterNodeAssignmentResponse.model_validate(data)

    async def report_runtime_event(
        self,
        request: AdapterDesktopRuntimeEventRequest,
    ) -> AdapterDesktopRuntimeEventAck:
        data = await self._request(
            "POST",
            "/internal/desktop/runtime-events",
            json=request.model_dump(exclude_none=True, mode="json"),
        )
        return AdapterDesktopRuntimeEventAck.model_validate(data)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


helix_adapter_client = HelixAdapterClient()


async def get_helix_adapter_client() -> HelixAdapterClient:
    return helix_adapter_client
