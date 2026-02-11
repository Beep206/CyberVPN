import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type UsageResponse = operations['get_usage_api_v1_users_me_usage_get']['responses'][200]['content']['application/json'];

/**
 * VPN Usage API client
 * Provides VPN bandwidth and connection usage statistics
 */
export const vpnApi = {
  /**
   * Get VPN usage statistics for authenticated user
   * GET /api/v1/users/me/usage
   *
   * Returns bandwidth usage (bytes used/limit), active/max connections,
   * billing period dates, and last connection timestamp.
   */
  getUsage: () =>
    apiClient.get<UsageResponse>('/users/me/usage'),
};
