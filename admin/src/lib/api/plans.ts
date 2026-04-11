import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type PlansResponse = operations['list_plans_api_v1_plans__get']['responses'][200]['content']['application/json'];
type CreatePlanRequest =
  operations['create_plan_api_v1_plans__post']['requestBody']['content']['application/json'];
type CreatePlanResponse =
  operations['create_plan_api_v1_plans__post']['responses'][200]['content']['application/json'];
type UpdatePlanRequest =
  operations['update_plan_api_v1_plans__uuid__put']['requestBody']['content']['application/json'];
type UpdatePlanResponse =
  operations['update_plan_api_v1_plans__uuid__put']['responses'][200]['content']['application/json'];
type DeletePlanResponse =
  operations['delete_plan_api_v1_plans__uuid__delete']['responses'][200]['content']['application/json'];

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

  /**
   * Create a new subscription plan.
   * POST /api/v1/plans
   */
  create: (data: CreatePlanRequest) =>
    apiClient.post<CreatePlanResponse>('/plans', data),

  /**
   * Update an existing subscription plan.
   * PUT /api/v1/plans/{uuid}
   */
  update: (uuid: string, data: UpdatePlanRequest) =>
    apiClient.put<UpdatePlanResponse>(`/plans/${uuid}`, data),

  /**
   * Delete an existing subscription plan.
   * DELETE /api/v1/plans/{uuid}
   */
  remove: (uuid: string) =>
    apiClient.delete<DeletePlanResponse>(`/plans/${uuid}`),
};
