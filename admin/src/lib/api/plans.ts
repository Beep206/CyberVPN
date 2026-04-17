import { apiClient } from './client';
import type { operations } from './generated/types';

type ListPlansOperation = operations['list_plans_api_v1_plans__get'];
type ListAdminPlansOperation = operations['list_admin_plans_api_v1_plans_admin_get'];

export type PlansResponse = ListPlansOperation['responses'][200]['content']['application/json'];
export type PlanRecord = PlansResponse[number];
export type ListPlansParams = ListPlansOperation['parameters']['query'];
export type AdminPlansResponse =
  ListAdminPlansOperation['responses'][200]['content']['application/json'];
export type ListAdminPlansParams = ListAdminPlansOperation['parameters']['query'];
export type CreatePlanRequest =
  operations['create_plan_api_v1_plans__post']['requestBody']['content']['application/json'];
export type CreatePlanResponse =
  operations['create_plan_api_v1_plans__post']['responses'][201]['content']['application/json'];
export type UpdatePlanRequest =
  operations['update_plan_api_v1_plans__uuid__put']['requestBody']['content']['application/json'];
export type UpdatePlanResponse =
  operations['update_plan_api_v1_plans__uuid__put']['responses'][200]['content']['application/json'];
export type DeletePlanResponse =
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
  list: (params?: ListPlansParams) =>
    apiClient.get<PlansResponse>('/plans', { params }),

  /**
   * List all canonical pricing catalog plans for admin tooling.
   * GET /api/v1/plans/admin
   */
  listAdmin: (params?: ListAdminPlansParams) =>
    apiClient.get<AdminPlansResponse>('/plans/admin', { params }),

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
