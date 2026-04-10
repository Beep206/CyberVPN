from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.dto.mobile_auth import SubscriptionStatus
from src.application.use_cases.subscriptions.get_active_subscription import (
    GetActiveSubscriptionUseCase,
)
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.helix.client import (
    AdapterClientCapabilityDefaults,
    AdapterDesktopRuntimeEventAck,
    AdapterDesktopRuntimeEventPayload,
    AdapterDesktopRuntimeEventRequest,
    AdapterNodeAssignmentResponse,
    AdapterNodeRegistryRecord,
    AdapterPublishRolloutRequest,
    AdapterResolveManifestRequest,
    AdapterResolveManifestResponse,
    AdapterRolloutBatchRecord,
    AdapterRolloutCanaryEvidenceResponse,
    AdapterRolloutStateResponse,
    AdapterTransportProfileRecord,
    HelixAdapterClient,
    HelixAdapterManifestUnavailableError,
)
from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient


class HelixDisabledError(RuntimeError):
    pass


class HelixAccessDeniedError(RuntimeError):
    pass


class HelixManifestUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolveManifestCommand:
    desktop_client_id: str | None = None
    trace_id: str | None = None
    channel: str | None = None
    supported_protocol_versions: list[int] | None = None
    supported_transport_profiles: list | None = None
    preferred_fallback_core: str | None = None


@dataclass(frozen=True)
class RuntimeEventCommand:
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
    payload: AdapterDesktopRuntimeEventPayload | dict | None = None


class HelixService:
    def __init__(
        self,
        adapter_client: HelixAdapterClient,
        subscription_client: CachedSubscriptionClient,
    ) -> None:
        self._adapter_client = adapter_client
        self._subscription_client = subscription_client

    def _ensure_user_feature_enabled(self) -> None:
        if not settings.helix_enabled:
            raise HelixDisabledError(
                "Helix user routes are disabled"
            )

    def _ensure_admin_feature_enabled(self) -> None:
        if not settings.helix_admin_enabled:
            raise HelixDisabledError(
                "Helix admin routes are disabled"
            )

    async def _ensure_entitled(self, user_id: UUID) -> str:
        subscription = await GetActiveSubscriptionUseCase(
            self._subscription_client
        ).execute(user_id)
        if subscription.status not in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
        }:
            raise HelixAccessDeniedError(
                "user is not entitled to Helix"
            )
        return f"subscription:{user_id}"

    async def get_capability_defaults_for_user(
        self,
        current_user: AdminUserModel,
    ) -> AdapterClientCapabilityDefaults:
        self._ensure_user_feature_enabled()
        await self._ensure_entitled(current_user.id)
        return await self._adapter_client.get_client_capability_defaults()

    async def resolve_manifest_for_user(
        self,
        current_user: AdminUserModel,
        command: ResolveManifestCommand,
    ) -> AdapterResolveManifestResponse:
        self._ensure_user_feature_enabled()
        entitlement_id = await self._ensure_entitled(current_user.id)

        request = AdapterResolveManifestRequest(
            user_id=str(current_user.id),
            desktop_client_id=command.desktop_client_id or f"desktop-{current_user.id}",
            entitlement_id=entitlement_id,
            trace_id=command.trace_id or str(uuid4()),
            channel=command.channel or settings.helix_default_channel,
            supported_protocol_versions=command.supported_protocol_versions,
            supported_transport_profiles=command.supported_transport_profiles,
            preferred_fallback_core=command.preferred_fallback_core,
        )
        try:
            return await self._adapter_client.resolve_manifest(request)
        except HelixAdapterManifestUnavailableError as error:
            raise HelixManifestUnavailableError(str(error)) from error

    async def report_runtime_event_for_user(
        self,
        current_user: AdminUserModel,
        command: RuntimeEventCommand,
    ) -> AdapterDesktopRuntimeEventAck:
        self._ensure_user_feature_enabled()
        await self._ensure_entitled(current_user.id)

        request = AdapterDesktopRuntimeEventRequest(
            event_id=str(uuid4()),
            user_id=str(current_user.id),
            desktop_client_id=command.desktop_client_id,
            manifest_version_id=command.manifest_version_id,
            rollout_id=command.rollout_id,
            transport_profile_id=command.transport_profile_id,
            event_kind=command.event_kind,
            active_core=command.active_core,
            fallback_core=command.fallback_core,
            latency_ms=command.latency_ms,
            route_count=command.route_count,
            reason=command.reason,
            observed_at=datetime.now(UTC),
            payload=AdapterDesktopRuntimeEventPayload.model_validate(
                command.payload or {}
            ),
        )
        return await self._adapter_client.report_runtime_event(request)

    async def list_nodes(self) -> list[AdapterNodeRegistryRecord]:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.list_nodes()

    async def get_rollout_status(self, rollout_id: str) -> AdapterRolloutStateResponse:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.get_rollout_status(rollout_id)

    async def get_rollout_canary_evidence(
        self,
        rollout_id: str,
    ) -> AdapterRolloutCanaryEvidenceResponse:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.get_rollout_canary_evidence(rollout_id)

    async def list_transport_profiles(self) -> list[AdapterTransportProfileRecord]:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.list_transport_profiles()

    async def publish_rollout(
        self,
        request: AdapterPublishRolloutRequest,
    ) -> AdapterRolloutBatchRecord:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.publish_rollout(request)

    async def pause_rollout(self, rollout_id: str) -> AdapterRolloutBatchRecord:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.pause_rollout(rollout_id)

    async def revoke_manifest(self, manifest_version_id: str):
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.revoke_manifest(manifest_version_id)

    async def preview_node_assignment(
        self, node_id: str
    ) -> AdapterNodeAssignmentResponse:
        self._ensure_admin_feature_enabled()
        return await self._adapter_client.resolve_node_assignment(node_id)
