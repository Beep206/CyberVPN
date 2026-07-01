import { apiClient } from './client';
import type { operations } from './generated/types';

type HostsResponse =
  operations['list_hosts_api_v1_hosts__get']['responses'][200]['content']['application/json'];
type HostResponse =
  operations['get_host_api_v1_hosts__uuid__get']['responses'][200]['content']['application/json'];
type CreateHostRequest =
  operations['create_host_api_v1_hosts__post']['requestBody']['content']['application/json'];
type CreateHostResponse =
  operations['create_host_api_v1_hosts__post']['responses'][200]['content']['application/json'];
type UpdateHostRequest =
  operations['update_host_api_v1_hosts__uuid__put']['requestBody']['content']['application/json'];
type UpdateHostResponse =
  operations['update_host_api_v1_hosts__uuid__put']['responses'][200]['content']['application/json'];

type ConfigProfilesResponse =
  operations['list_config_profiles_api_v1_config_profiles__get']['responses'][200]['content']['application/json'];
type CreateConfigProfileRequest =
  operations['create_config_profile_api_v1_config_profiles__post']['requestBody']['content']['application/json'];
type CreateConfigProfileResponse =
  operations['create_config_profile_api_v1_config_profiles__post']['responses'][200]['content']['application/json'];

type InboundsResponse =
  operations['list_inbounds_api_v1_inbounds__get']['responses'][200]['content']['application/json'];
type InboundResponse =
  operations['get_inbound_api_v1_inbounds__uuid__get']['responses'][200]['content']['application/json'];

type NodePluginsResponse =
  operations['list_node_plugins_api_v1_node_plugins__get']['responses'][200]['content']['application/json'];
type NodePluginResponse =
  operations['get_node_plugin_api_v1_node_plugins__uuid__get']['responses'][200]['content']['application/json'];
type CreateNodePluginRequest =
  operations['create_node_plugin_api_v1_node_plugins__post']['requestBody']['content']['application/json'];
type CreateNodePluginResponse =
  operations['create_node_plugin_api_v1_node_plugins__post']['responses'][200]['content']['application/json'];
type UpdateNodePluginRequest =
  operations['update_node_plugin_api_v1_node_plugins__uuid__put']['requestBody']['content']['application/json'];
type UpdateNodePluginResponse =
  operations['update_node_plugin_api_v1_node_plugins__uuid__put']['responses'][200]['content']['application/json'];
type DeleteNodePluginResponse =
  operations['delete_node_plugin_api_v1_node_plugins__uuid__delete']['responses'][200]['content']['application/json'];
type CloneNodePluginRequest =
  operations['clone_node_plugin_api_v1_node_plugins_clone_post']['requestBody']['content']['application/json'];
type CloneNodePluginResponse =
  operations['clone_node_plugin_api_v1_node_plugins_clone_post']['responses'][200]['content']['application/json'];
type ExecuteNodePluginRequest =
  operations['execute_node_plugin_api_v1_node_plugins_execute_post']['requestBody']['content']['application/json'];
type ExecuteNodePluginResponse =
  operations['execute_node_plugin_api_v1_node_plugins_execute_post']['responses'][200]['content']['application/json'];
type TorrentBlockerStatsResponse =
  operations['get_torrent_blocker_stats_api_v1_node_plugins_torrent_blocker_stats_get']['responses'][200]['content']['application/json'];

type InternalSquadsResponse =
  operations['list_internal_squads_api_v1_squads_internal_get']['responses'][200]['content']['application/json'];
type ExternalSquadsResponse =
  operations['list_external_squads_api_v1_squads_external_get']['responses'][200]['content']['application/json'];
type CreateSquadRequest =
  operations['create_squad_api_v1_squads__post']['requestBody']['content']['application/json'] & {
    inbounds?: string[];
  };
type CreateSquadResponse =
  operations['create_squad_api_v1_squads__post']['responses'][200]['content']['application/json'];

type SnippetsResponse =
  operations['list_snippets_api_v1_snippets__get']['responses'][200]['content']['application/json'];
type CreateSnippetRequest =
  operations['create_snippet_api_v1_snippets__post']['requestBody']['content']['application/json'];
type CreateSnippetResponse =
  operations['create_snippet_api_v1_snippets__post']['responses'][200]['content']['application/json'];

type XrayConfigResponse =
  operations['get_xray_config_api_v1_xray_config_get']['responses'][200]['content']['application/json'];
type UpdateXrayConfigRequest =
  operations['update_xray_config_api_v1_xray_update_config_post']['requestBody']['content']['application/json'];
type UpdateXrayConfigResponse =
  operations['update_xray_config_api_v1_xray_update_config_post']['responses'][200]['content']['application/json'];

type HelixNodesResponse =
  operations['list_nodes_api_v1_helix_admin_nodes_get']['responses'][200]['content']['application/json'];
type HelixTransportProfilesResponse =
  operations['list_transport_profiles_api_v1_helix_admin_transport_profiles_get']['responses'][200]['content']['application/json'];
type HelixRolloutStateResponse =
  operations['get_rollout_status_api_v1_helix_admin_rollouts__rollout_id__get']['responses'][200]['content']['application/json'];
type HelixCanaryEvidenceResponse =
  operations['get_rollout_canary_evidence_api_v1_helix_admin_rollouts__rollout_id__canary_evidence_get']['responses'][200]['content']['application/json'];
type HelixPublishRolloutRequest =
  operations['publish_rollout_api_v1_helix_admin_rollouts_post']['requestBody']['content']['application/json'];
type HelixPublishRolloutResponse =
  operations['publish_rollout_api_v1_helix_admin_rollouts_post']['responses'][200]['content']['application/json'];
type HelixPauseRolloutResponse =
  operations['pause_rollout_api_v1_helix_admin_rollouts__rollout_id__pause_post']['responses'][200]['content']['application/json'];
type HelixRevokeManifestResponse =
  operations['revoke_manifest_api_v1_helix_admin_manifests__manifest_version_id__revoke_post']['responses'][200]['content']['application/json'];
type HelixNodeAssignmentResponse =
  operations['preview_node_assignment_api_v1_helix_admin_nodes__node_id__assignment_get']['responses'][200]['content']['application/json'];

export const hostsApi = {
  list: () =>
    apiClient.get<HostsResponse>('/hosts/'),
  get: (uuid: string) =>
    apiClient.get<HostResponse>(`/hosts/${uuid}`),
  create: (data: CreateHostRequest) =>
    apiClient.post<CreateHostResponse>('/hosts/', data),
  update: (uuid: string, data: UpdateHostRequest) =>
    apiClient.put<UpdateHostResponse>(`/hosts/${uuid}`, data),
  remove: (uuid: string) =>
    apiClient.delete(`/hosts/${uuid}`),
};

export const configProfilesApi = {
  list: () =>
    apiClient.get<ConfigProfilesResponse>('/config-profiles/'),
  create: (data: CreateConfigProfileRequest) =>
    apiClient.post<CreateConfigProfileResponse>('/config-profiles/', data),
};

export const inboundsApi = {
  list: () =>
    apiClient.get<InboundsResponse>('/inbounds/'),
  get: (uuid: string) =>
    apiClient.get<InboundResponse>(`/inbounds/${uuid}`),
};

export const nodePluginsApi = {
  list: () =>
    apiClient.get<NodePluginsResponse>('/node-plugins/'),
  get: (uuid: string) =>
    apiClient.get<NodePluginResponse>(`/node-plugins/${uuid}`),
  create: (data: CreateNodePluginRequest) =>
    apiClient.post<CreateNodePluginResponse>('/node-plugins/', data),
  update: (uuid: string, data: UpdateNodePluginRequest) =>
    apiClient.put<UpdateNodePluginResponse>(`/node-plugins/${uuid}`, data),
  remove: (uuid: string) =>
    apiClient.delete<DeleteNodePluginResponse>(`/node-plugins/${uuid}`),
  clone: (data: CloneNodePluginRequest) =>
    apiClient.post<CloneNodePluginResponse>('/node-plugins/clone', data),
  execute: (data: ExecuteNodePluginRequest) =>
    apiClient.post<ExecuteNodePluginResponse>('/node-plugins/execute', data),
  getTorrentStats: () =>
    apiClient.get<TorrentBlockerStatsResponse>('/node-plugins/torrent-blocker/stats'),
};

export const squadsApi = {
  listInternal: () =>
    apiClient.get<InternalSquadsResponse>('/squads/internal'),
  listExternal: () =>
    apiClient.get<ExternalSquadsResponse>('/squads/external'),
  create: (data: CreateSquadRequest) =>
    apiClient.post<CreateSquadResponse>('/squads/', data),
};

export const snippetsApi = {
  list: () =>
    apiClient.get<SnippetsResponse>('/snippets/'),
  create: (data: CreateSnippetRequest) =>
    apiClient.post<CreateSnippetResponse>('/snippets/', data),
};

export const xrayApi = {
  getConfig: () =>
    apiClient.get<XrayConfigResponse>('/xray/config'),
  updateConfig: (data: UpdateXrayConfigRequest) =>
    apiClient.post<UpdateXrayConfigResponse>('/xray/update-config', data),
};

export const helixApi = {
  listNodes: () =>
    apiClient.get<HelixNodesResponse>('/helix/admin/nodes'),
  listTransportProfiles: () =>
    apiClient.get<HelixTransportProfilesResponse>('/helix/admin/transport-profiles'),
  getRolloutStatus: (rolloutId: string) =>
    apiClient.get<HelixRolloutStateResponse>(`/helix/admin/rollouts/${rolloutId}`),
  getCanaryEvidence: (rolloutId: string) =>
    apiClient.get<HelixCanaryEvidenceResponse>(
      `/helix/admin/rollouts/${rolloutId}/canary-evidence`,
    ),
  publishRollout: (data: HelixPublishRolloutRequest) =>
    apiClient.post<HelixPublishRolloutResponse>('/helix/admin/rollouts', data),
  pauseRollout: (rolloutId: string) =>
    apiClient.post<HelixPauseRolloutResponse>(`/helix/admin/rollouts/${rolloutId}/pause`, {}),
  revokeManifest: (manifestVersionId: string) =>
    apiClient.post<HelixRevokeManifestResponse>(
      `/helix/admin/manifests/${manifestVersionId}/revoke`,
      {},
    ),
  previewNodeAssignment: (nodeId: string) =>
    apiClient.get<HelixNodeAssignmentResponse>(`/helix/admin/nodes/${nodeId}/assignment`),
};

export interface VpnTesterResult {
  id: string;
  check_key: string;
  check_name: string;
  category: string;
  status: 'pass' | 'fail' | 'degraded' | 'skipped' | string;
  severity: string;
  target: string;
  safe_summary: string;
  details: Record<string, unknown>;
  duration_ms: number;
  created_at: string;
}

export interface VpnTesterEvidenceArtifact {
  id: string;
  artifact_key: string;
  artifact_type: string;
  sha256: string;
  preview: Record<string, unknown>;
  storage_uri: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface VpnTesterRun {
  id: string;
  suite_key: string;
  suite_version: string;
  mode: string;
  trigger: string;
  status: 'queued' | 'running' | 'pass' | 'fail' | 'degraded' | 'skipped' | 'cancelled' | string;
  requested_by_admin_id: string | null;
  agent_id: string | null;
  runtime_mode: string | null;
  route_registry_version: string | null;
  blocking: boolean;
  summary: Record<string, unknown>;
  pass_count: number;
  fail_count: number;
  degraded_count: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
  results: VpnTesterResult[];
  evidence_artifacts: VpnTesterEvidenceArtifact[];
}

export interface VpnTesterSchedule {
  id: string;
  schedule_key: string;
  suite_key: string;
  mode: string;
  cron: string;
  enabled: boolean;
  settings: Record<string, unknown>;
  next_run_at: string | null;
  last_run_id: string | null;
  last_status: string | null;
  last_skipped_reason: string | null;
  last_checked_at: string | null;
  last_triggered_at: string | null;
  schedule_source: string;
  updated_at: string;
}

export interface VpnTesterOverview {
  enabled: boolean;
  runtime_enabled: boolean;
  scheduled_enabled: boolean;
  balancer_recommendations_enabled: boolean;
  counts: Record<string, number>;
  latest_runs: VpnTesterRun[];
  schedules: VpnTesterSchedule[];
  generated_at: string;
}

export interface CreateVpnTesterRunRequest {
  suite_key: string;
  mode: 'contract' | 'runtime' | 'all_tariffs' | 'balancer_preview';
  context?: Record<string, unknown>;
}

export interface UpdateVpnTesterScheduleRequest {
  enabled: boolean;
  settings?: Record<string, unknown>;
}

export interface VpnTesterTariffMatrix {
  rows: Array<Record<string, unknown>>;
  total: number;
  generated_at: string;
}

export interface VpnTesterRouteMatrix {
  registry_key: string;
  rows: Array<Record<string, unknown>>;
  total: number;
  generated_at: string;
}

export interface VpnTesterReleaseGateOverride {
  id: string;
  latest_run_id: string | null;
  overridden_by_admin_id: string | null;
  previous_status: string;
  previous_blocking: boolean;
  reason: string;
  expires_at: string;
  created_at: string;
}

export interface VpnTesterReleaseGate {
  status: string;
  blocking: boolean;
  latest_run_id: string | null;
  reason: string;
  override_allowed_roles: string[];
  active_override: VpnTesterReleaseGateOverride | null;
  generated_at: string;
}

export interface CreateReleaseGateOverrideRequest {
  reason: string;
  ttl_minutes: number;
}

export interface DismissBalancerRecommendationRequest {
  reason?: string | null;
}

export interface VpnBalancerRecommendation {
  id: string;
  recommendation_key: string;
  recommendation_hash: string;
  run_id: string | null;
  status: string;
  scope: string;
  safe_summary: string;
  candidate_changes: Record<string, unknown>;
  confidence: number;
  acknowledged_by_admin_id: string | null;
  acknowledged_at: string | null;
  dismissed_by_admin_id: string | null;
  dismissed_at: string | null;
  dismissed_reason: string | null;
  applied_manually_by_admin_id: string | null;
  applied_manually_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export const vpnTesterApi = {
  overview: () =>
    apiClient.get<VpnTesterOverview>('/admin/vpn-tester/overview'),
  listRuns: (params?: { limit?: number; status_filter?: string }) =>
    apiClient.get<VpnTesterRun[]>('/admin/vpn-tester/runs', { params }),
  createRun: (data: CreateVpnTesterRunRequest) =>
    apiClient.post<VpnTesterRun>('/admin/vpn-tester/runs', data),
  getRun: (runId: string) =>
    apiClient.get<VpnTesterRun>(`/admin/vpn-tester/runs/${runId}`),
  cancelRun: (runId: string) =>
    apiClient.post<VpnTesterRun>(`/admin/vpn-tester/runs/${runId}/cancel`, {}),
  listEvidence: (runId: string) =>
    apiClient.get<VpnTesterEvidenceArtifact[]>(`/admin/vpn-tester/runs/${runId}/evidence`),
  listSchedules: () =>
    apiClient.get<VpnTesterSchedule[]>('/admin/vpn-tester/schedules'),
  updateSchedule: (scheduleKey: string, data: UpdateVpnTesterScheduleRequest) =>
    apiClient.put<VpnTesterSchedule>(
      `/admin/vpn-tester/schedules/${encodeURIComponent(scheduleKey)}`,
      data,
    ),
  tariffMatrix: () =>
    apiClient.get<VpnTesterTariffMatrix>('/admin/vpn-tester/tariffs'),
  routeMatrix: () =>
    apiClient.get<VpnTesterRouteMatrix>('/admin/vpn-tester/route-matrix'),
  balancerPreview: () =>
    apiClient.get<Record<string, unknown>>('/admin/vpn-tester/balancer/preview'),
  listBalancerRecommendations: (params?: { limit?: number }) =>
    apiClient.get<VpnBalancerRecommendation[]>('/admin/vpn-tester/balancer/recommendations', { params }),
  acknowledgeBalancerRecommendation: (recommendationId: string) =>
    apiClient.post<VpnBalancerRecommendation>(
      `/admin/vpn-tester/balancer/recommendations/${recommendationId}/ack`,
      {},
    ),
  dismissBalancerRecommendation: (
    recommendationId: string,
    data: DismissBalancerRecommendationRequest,
  ) =>
    apiClient.post<VpnBalancerRecommendation>(
      `/admin/vpn-tester/balancer/recommendations/${recommendationId}/dismiss`,
      data,
    ),
  releaseGate: () =>
    apiClient.get<VpnTesterReleaseGate>('/admin/vpn-tester/release-gate'),
  overrideReleaseGate: (data: CreateReleaseGateOverrideRequest) =>
    apiClient.post<VpnTesterReleaseGate>('/admin/vpn-tester/release-gate/override', data),
};
