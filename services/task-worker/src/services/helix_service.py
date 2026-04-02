"""Helix adapter client for task-worker automation.

Provides a typed async client around the Helix adapter so worker
jobs can audit rollout health and stale-node conditions without talking to the
adapter in an ad-hoc way.
"""

from __future__ import annotations

from datetime import datetime

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field

from src.config import get_settings

logger = structlog.get_logger(__name__)


class HelixAdapterError(Exception):
    """Raised when the Helix adapter cannot fulfill a request."""


class AdapterModel(BaseModel):
    """Base model for adapter responses."""

    model_config = ConfigDict(extra="ignore")


class HelixNodeRecord(AdapterModel):
    """Transport-enabled node entry returned by the adapter."""

    remnawave_node_id: str
    node_name: str
    transport_enabled: bool
    rollout_channel: str
    active_rollout_id: str | None = None
    last_heartbeat_at: datetime | None = None
    daemon_version: str | None = None


class HelixRolloutBatchSummary(AdapterModel):
    batch_id: str
    manifest_version: str
    target_nodes: int
    completed_nodes: int
    failed_nodes: int


class HelixRolloutNodeSummary(AdapterModel):
    healthy: int
    stale: int
    rolled_back: int


class HelixRolloutDesktopSummary(AdapterModel):
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


class HelixTransportProfilePolicySummary(AdapterModel):
    observed_events: int = 0
    connect_success_rate: float = 0.0
    fallback_rate: float = 0.0
    continuity_success_rate: float = 0.0
    cross_route_recovery_rate: float = 0.0
    policy_score: int = 0
    degraded: bool = False
    advisory_state: str = "healthy"
    recommended_action: str | None = None
    selection_eligible: bool = True
    new_session_issuable: bool = True
    new_session_posture: str = "preferred"
    suppression_window_active: bool = False
    suppression_reason: str | None = None
    suppression_observation_count: int = 0
    suppressed_until: datetime | None = None


class HelixRolloutPolicySummary(AdapterModel):
    pause_on_rollback_spike: bool = False
    revoke_on_manifest_error: bool = False
    active_transport_profile_id: str | None = None
    active_profile_policy: HelixTransportProfilePolicySummary | None = None
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


class HelixRolloutState(AdapterModel):
    rollout_id: str
    channel: str
    desired_state: str
    current_batch: HelixRolloutBatchSummary
    nodes: HelixRolloutNodeSummary
    desktop: HelixRolloutDesktopSummary
    policy: HelixRolloutPolicySummary = Field(
        default_factory=HelixRolloutPolicySummary
    )


class HelixRolloutCanaryThresholdSummary(AdapterModel):
    min_connect_success_rate: float
    max_fallback_rate: float
    min_continuity_observations: int
    require_throughput_evidence: bool
    min_relative_throughput_ratio: float
    max_relative_open_to_first_byte_gap_ratio: float
    min_continuity_success_rate: float
    min_cross_route_recovery_rate: float


class HelixRolloutCanarySnapshotSummary(AdapterModel):
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


class HelixRolloutCanaryEvidence(AdapterModel):
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
    thresholds: HelixRolloutCanaryThresholdSummary
    snapshot: HelixRolloutCanarySnapshotSummary


class HelixService:
    """Typed worker-facing client for the Helix adapter."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.helix_adapter_url).rstrip(
            "/"
        )
        self._token = (
            token or settings.helix_adapter_token.get_secret_value()
        )
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HelixService":
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0),
                headers={"x-internal-token": self._token},
                transport=self._transport,
            )
        return self._client

    async def _request(self, method: str, path: str) -> list | dict:
        client = await self._get_client()
        try:
            response = await client.request(method, path)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            logger.error(
                "helix_adapter_request_failed",
                method=method,
                path=path,
                error=str(error),
            )
            raise HelixAdapterError(
                f"Helix adapter request failed: {error}"
            ) from error

    async def list_nodes(self) -> list[HelixNodeRecord]:
        """Fetch node inventory from the adapter admin surface."""
        data = await self._request("GET", "/admin/nodes")
        return [HelixNodeRecord.model_validate(item) for item in data]

    async def get_rollout_status(self, rollout_id: str) -> HelixRolloutState:
        """Fetch rollout status from the adapter internal surface."""
        data = await self._request("GET", f"/internal/rollouts/{rollout_id}/status")
        return HelixRolloutState.model_validate(data)

    async def get_rollout_canary_evidence(
        self,
        rollout_id: str,
    ) -> HelixRolloutCanaryEvidence:
        """Fetch formal canary evidence snapshot from the adapter internal surface."""
        data = await self._request(
            "GET", f"/internal/rollouts/{rollout_id}/canary-evidence"
        )
        return HelixRolloutCanaryEvidence.model_validate(data)

    async def list_active_rollout_states(self) -> list[HelixRolloutState]:
        """Resolve rollout states for every active transport rollout in the node registry."""
        nodes = await self.list_nodes()
        rollout_ids = sorted(
            {
                node.active_rollout_id
                for node in nodes
                if node.transport_enabled and node.active_rollout_id
            }
        )
        return [await self.get_rollout_status(rollout_id) for rollout_id in rollout_ids]

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
