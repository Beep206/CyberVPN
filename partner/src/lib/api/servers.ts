import type { AxiosResponse } from 'axios';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ServersResponse = operations['list_servers_api_v1_servers__get']['responses'][200]['content']['application/json'];
type ServerStatsResponse = operations['get_server_stats_api_v1_servers_stats_get']['responses'][200]['content']['application/json'];
type ServerResponse = operations['get_server_api_v1_servers__server_id__get']['responses'][200]['content']['application/json'];
type CreateServerRequest =
  operations['create_server_api_v1_servers__post']['requestBody']['content']['application/json'];
type CreateServerResponse =
  operations['create_server_api_v1_servers__post']['responses'][201]['content']['application/json'];
type UpdateServerRequest =
  operations['update_server_api_v1_servers__server_id__put']['requestBody']['content']['application/json'];
type UpdateServerResponse =
  operations['update_server_api_v1_servers__server_id__put']['responses'][200]['content']['application/json'];

export const GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE =
  'GLOBAL_SERVER_TOPOLOGY_ADMIN_ONLY' as const;

export class GlobalServerTopologyUnavailableError extends Error {
  readonly code = GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE;

  constructor() {
    super('Global server topology is available only in the private admin application.');
    this.name = 'GlobalServerTopologyUnavailableError';
  }
}

function rejectGlobalServerTopology<T>(...context: unknown[]): Promise<AxiosResponse<T>> {
  void context;
  return Promise.reject(new GlobalServerTopologyUnavailableError());
}

/**
 * Retired partner client for the admin-only global server topology API.
 * Partner surfaces must use workspace/grant-scoped Remnawave projections.
 */
export const serversApi = {
  list: (): Promise<AxiosResponse<ServersResponse>> =>
    rejectGlobalServerTopology(),
  create: (data: CreateServerRequest): Promise<AxiosResponse<CreateServerResponse>> =>
    rejectGlobalServerTopology(data),
  getStats: (): Promise<AxiosResponse<ServerStatsResponse>> =>
    rejectGlobalServerTopology(),
  get: (serverId: string): Promise<AxiosResponse<ServerResponse>> =>
    rejectGlobalServerTopology(serverId),
  update: (
    serverId: string,
    data: UpdateServerRequest,
  ): Promise<AxiosResponse<UpdateServerResponse>> => rejectGlobalServerTopology(serverId, data),
  remove: (serverId: string): Promise<AxiosResponse<void>> =>
    rejectGlobalServerTopology(serverId),
};
