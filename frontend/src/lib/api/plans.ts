import { apiClient } from './client';
import type { operations } from './generated/types';

type ListPlansOperation = operations['list_plans_api_v1_plans__get'];

export type PlansResponse = ListPlansOperation['responses'][200]['content']['application/json'];
export type PlanRecord = PlansResponse[number];
export type ListPlansParams = ListPlansOperation['parameters']['query'];

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
  list: (params?: ListPlansParams) =>
    apiClient.get<PlansResponse>('/plans', { params }),
};
