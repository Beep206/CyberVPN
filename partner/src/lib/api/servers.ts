import { apiClient } from './client';
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

/**
 * Servers API client
 * Manages VPN server list, stats, and individual server details
 */
export const serversApi = {
  /**
   * List all VPN servers
   * GET /api/v1/servers/
   *
   * Returns all configured VPN servers with their status, location, and load.
   */
  list: () =>
    apiClient.get<ServersResponse>('/servers/'),

  /**
   * Create a new VPN server.
   * POST /api/v1/servers/
   */
  create: (data: CreateServerRequest) =>
    apiClient.post<CreateServerResponse>('/servers/', data),

  /**
   * Get aggregated server statistics
   * GET /api/v1/servers/stats
   *
   * Returns system-wide server metrics:
   * - Total servers count
   * - Online/offline breakdown
   * - Average load across all servers
   * - Total bandwidth usage
   */
  getStats: () =>
    apiClient.get<ServerStatsResponse>('/servers/stats'),

  /**
   * Get individual server details
   * GET /api/v1/servers/{server_id}
   *
   * Returns detailed information about a specific server including
   * real-time metrics, connection limits, and configuration.
   *
   * @param serverId - Server ID
   * @throws 404 - Server not found
   */
  get: (serverId: string) =>
    apiClient.get<ServerResponse>(`/servers/${serverId}`),

  /**
   * Update a VPN server by UUID.
   * PUT /api/v1/servers/{server_id}
   */
  update: (serverId: string, data: UpdateServerRequest) =>
    apiClient.put<UpdateServerResponse>(`/servers/${serverId}`, data),

  /**
   * Delete a VPN server by UUID.
   * DELETE /api/v1/servers/{server_id}
   */
  remove: (serverId: string) =>
    apiClient.delete<void>(`/servers/${serverId}`),
};
