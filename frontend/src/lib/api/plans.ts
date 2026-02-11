import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type PlansResponse = operations['list_plans_api_v1_plans__get']['responses'][200]['content']['application/json'];

/**
 * Plans API client
 * Manages subscription plans (pricing, features, limits)
 */
export const plansApi = {
  /**
   * List all available subscription plans
   * GET /api/v1/plans
   *
   * Returns all public subscription plans with pricing, features, and limits.
   * Plans are displayed to users for purchase selection.
   */
  list: () =>
    apiClient.get<PlansResponse>('/plans'),
};
