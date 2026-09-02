import type { AxiosResponse } from 'axios';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type ServersResponse = operations['list_servers_api_v1_servers__get']['responses'][200]['content']['application/json'];
type ServerStatsResponse = operations['get_server_stats_api_v1_servers_stats_get']['responses'][200]['content']['application/json'];
type ServerResponse = operations['get_server_api_v1_servers__server_id__get']['responses'][200]['content']['application/json'];

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
 * Retired customer client for the admin-only global server topology API.
 * Customer surfaces must use account-scoped service/config projections instead.
 */
export const serversApi = {
  list: (): Promise<AxiosResponse<ServersResponse>> =>
    rejectGlobalServerTopology(),
  getStats: (): Promise<AxiosResponse<ServerStatsResponse>> =>
    rejectGlobalServerTopology(),
  get: (serverId: string): Promise<AxiosResponse<ServerResponse>> =>
    rejectGlobalServerTopology(serverId),
};
