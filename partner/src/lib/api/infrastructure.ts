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
