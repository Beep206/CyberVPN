import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type UsageResponse = operations['get_usage_api_v1_users_me_usage_get']['responses'][200]['content']['application/json'];

/**
 * Usage API client
 * Fetches user VPN usage statistics (bandwidth, connections)
 */
export const usageApi = {
  /**
   * Get authenticated user's VPN usage
   * GET /api/v1/users/me/usage
   *
   * Returns bandwidth used/limit and connection count.
   */
  getMyUsage: () =>
    apiClient.get<UsageResponse>('/users/me/usage'),
};
