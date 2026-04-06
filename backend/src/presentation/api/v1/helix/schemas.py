from pydantic import BaseModel, ConfigDict, Field

from src.infrastructure.helix.client import (
    AdapterClientCapabilityDefaults,
    AdapterDesktopRuntimeEventAck,
    AdapterDesktopRuntimeEventPayload,
    AdapterManifestVersionRecord,
    AdapterNodeAssignmentResponse,
    AdapterNodeRegistryRecord,
    AdapterResolveManifestResponse,
    AdapterRolloutBatchRecord,
    AdapterRolloutCanaryEvidenceResponse,
    AdapterRolloutStateResponse,
    AdapterSupportedTransportProfile,
    AdapterTransportProfileRecord,
)


class HelixResolveManifestRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "desktop_client_id": "desktop-win11-primary",
                "channel": "lab",
                "supported_protocol_versions": [1],
                "supported_transport_profiles": [
                    {
                        "profile_family": "edge-hybrid",
                        "min_transport_profile_version": 1,
                        "max_transport_profile_version": 4,
                        "supported_policy_versions": [4, 5, 6, 7],
                    }
                ],
                "preferred_fallback_core": "sing-box",
            }
        }
    )

    desktop_client_id: str | None = Field(default=None, min_length=3, max_length=128)
    trace_id: str | None = Field(default=None, min_length=8, max_length=128)
    channel: str | None = Field(default=None, pattern="^(lab|canary|stable)$")
    supported_protocol_versions: list[int] | None = None
    supported_transport_profiles: list[AdapterSupportedTransportProfile] | None = None
    preferred_fallback_core: str | None = Field(
        default=None, pattern="^(sing-box|xray)$"
    )


class HelixPublishRolloutRequest(BaseModel):
    rollout_id: str = Field(..., pattern="^rollout-[a-z0-9-]+$")
    batch_id: str = Field(..., min_length=3, max_length=128)
    channel: str = Field(..., pattern="^(lab|canary|stable)$")
    manifest_version: str = Field(..., min_length=1, max_length=128)
    target_node_ids: list[str] = Field(..., min_length=1)
    pause_on_rollback_spike: bool = True
    revoke_on_manifest_error: bool = True


class HelixRuntimeEventRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "desktop_client_id": "desktop-win11-primary",
                "manifest_version_id": "de33fcba-b71d-4f5f-82d2-34ae78977e31",
                "rollout_id": "rollout-lab-1",
                "transport_profile_id": "ptp-lab-edge-v2",
                "event_kind": "ready",
                "active_core": "helix",
                "latency_ms": 142,
                "route_count": 2,
                "payload": {
                    "runtime": "embedded-sidecar",
                    "status": "ready",
                    "continuity": {
                        "active_streams": 3,
                        "pending_open_streams": 0,
                        "continuity_grace_active": False,
                        "successful_continuity_recovers": 2,
                    },
                    "recovery": {
                        "same_route_recovered": True,
                        "ready_recovery_latency_ms": 41,
                        "proxy_ready_latency_ms": 56,
                    },
                    "benchmark": {
                        "benchmark_kind": "comparison",
                        "baseline_core": "sing-box",
                        "throughput_kbps": 68400.0,
                        "relative_throughput_ratio_vs_baseline": 0.97,
                        "median_open_to_first_byte_gap_ms": 24,
                        "relative_open_to_first_byte_gap_ratio_vs_baseline": 1.04,
                    },
                },
            }
        }
    )

    desktop_client_id: str = Field(..., min_length=3, max_length=128)
    manifest_version_id: str = Field(..., min_length=36, max_length=64)
    rollout_id: str = Field(..., pattern="^rollout-[a-z0-9-]+$")
    transport_profile_id: str = Field(..., min_length=3, max_length=128)
    event_kind: str = Field(..., pattern="^(ready|fallback|disconnect|benchmark)$")
    active_core: str = Field(
        ..., pattern="^(helix|private-transport|sing-box|xray)$"
    )
    fallback_core: str | None = Field(default=None, pattern="^(sing-box|xray)$")
    latency_ms: int | None = Field(default=None, ge=0)
    route_count: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=512)
    payload: AdapterDesktopRuntimeEventPayload = Field(
        default_factory=AdapterDesktopRuntimeEventPayload
    )


HelixCapabilityDefaultsResponse = AdapterClientCapabilityDefaults
HelixResolveManifestResponse = AdapterResolveManifestResponse
HelixRuntimeEventResponse = AdapterDesktopRuntimeEventAck
HelixNodeListResponse = list[AdapterNodeRegistryRecord]
HelixRolloutStateResponse = AdapterRolloutStateResponse
HelixRolloutCanaryEvidenceResponse = AdapterRolloutCanaryEvidenceResponse
HelixTransportProfilesResponse = list[AdapterTransportProfileRecord]
HelixRolloutBatchResponse = AdapterRolloutBatchRecord
HelixManifestVersionResponse = AdapterManifestVersionRecord
HelixNodeAssignmentPreviewResponse = AdapterNodeAssignmentResponse
