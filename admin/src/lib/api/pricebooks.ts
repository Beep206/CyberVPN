import { apiClient } from './client';
import type { operations } from './generated/types';

type ResolvePricebooksOperation =
  operations['resolve_pricebooks_api_v1_pricebooks_resolve_get'];
type ListAdminPricebooksOperation =
  operations['list_admin_pricebooks_api_v1_pricebooks_admin_get'];
type ListAdminCommercialPricebooksOperation =
  operations['list_admin_commercial_pricebooks_api_v1_admin_pricebooks_get'];
type UpdateAdminCommercialPricebookOperation =
  operations['update_admin_commercial_pricebook_api_v1_admin_pricebooks__pricebook_id__patch'];
type PublishAdminPricebookOperation =
  operations['publish_admin_commercial_pricebook_api_v1_admin_pricebooks__pricebook_id__publish_post'];
type ScheduleAdminPricebookOperation =
  operations['schedule_admin_commercial_pricebook_api_v1_admin_pricebooks__pricebook_id__schedule_post'];
type RollbackAdminPricebookOperation =
  operations['rollback_admin_commercial_pricebook_api_v1_admin_pricebooks__pricebook_id__rollback_post'];
type GetAdminPricebookHistoryOperation =
  operations['get_admin_commercial_pricebook_history_api_v1_admin_pricebooks__pricebook_key__history_get'];
type GetAdminPricebookAuditOperation =
  operations['get_admin_commercial_pricebook_audit_api_v1_admin_pricebooks__pricebook_id__audit_get'];
type ValidateAdminPricebookOperation =
  operations['validate_admin_commercial_pricebook_api_v1_admin_pricebooks__pricebook_id__validate_post'];
type GetCommercialContextOptionsOperation =
  operations['get_admin_commercial_context_options_api_v1_admin_commercial_context_options_get'];
type UpdateCommercialContextOptionsOperation =
  operations['update_admin_commercial_context_options_api_v1_admin_commercial_context_options_put'];
type CreatePricebookOperation =
  operations['create_pricebook_api_v1_pricebooks__post'];

export type PricebooksResponse =
  ResolvePricebooksOperation['responses'][200]['content']['application/json'];
export type PricebookRecord = PricebooksResponse[number];
export type ResolvePricebooksParams =
  ResolvePricebooksOperation['parameters']['query'];
export type AdminPricebooksResponse =
  ListAdminPricebooksOperation['responses'][200]['content']['application/json'];
export type ListAdminPricebooksParams =
  ListAdminPricebooksOperation['parameters']['query'];
export type AdminCommercialPricebooksResponse =
  ListAdminCommercialPricebooksOperation['responses'][200]['content']['application/json'];
export type AdminCommercialPricebookRecord =
  AdminCommercialPricebooksResponse[number];
export type ListAdminCommercialPricebooksParams =
  ListAdminCommercialPricebooksOperation['parameters']['query'];
export type UpdateAdminPricebookRequest =
  UpdateAdminCommercialPricebookOperation['requestBody']['content']['application/json'];
export type AdminPricebookLifecycleResponse =
  UpdateAdminCommercialPricebookOperation['responses'][200]['content']['application/json'];
export type PublishAdminPricebookRequest =
  PublishAdminPricebookOperation['requestBody']['content']['application/json'];
export type ScheduleAdminPricebookRequest =
  ScheduleAdminPricebookOperation['requestBody']['content']['application/json'];
export type RollbackAdminPricebookRequest =
  RollbackAdminPricebookOperation['requestBody']['content']['application/json'];
export type AdminPricebookHistoryResponse =
  GetAdminPricebookHistoryOperation['responses'][200]['content']['application/json'];
export type AdminPricebookAuditParams =
  GetAdminPricebookAuditOperation['parameters']['query'];
export type AdminPricebookAuditResponse =
  GetAdminPricebookAuditOperation['responses'][200]['content']['application/json'];
export type AdminPricebookValidationResponse =
  ValidateAdminPricebookOperation['responses'][200]['content']['application/json'];
export type CommercialContextOptionsResponse =
  GetCommercialContextOptionsOperation['responses'][200]['content']['application/json'];
export type UpdateCommercialContextOptionsRequest =
  UpdateCommercialContextOptionsOperation['requestBody']['content']['application/json'];
export type CreatePricebookRequest =
  CreatePricebookOperation['requestBody']['content']['application/json'];
export type CreatePricebookResponse =
  CreatePricebookOperation['responses'][201]['content']['application/json'];
export type PricebookEntryRequest = NonNullable<
  CreatePricebookRequest['entries']
>[number];

export const pricebooksApi = {
  resolve: (params?: ResolvePricebooksParams) =>
    apiClient.get<PricebooksResponse>('/pricebooks/resolve', { params }),

  listAdmin: (params?: ListAdminPricebooksParams) =>
    apiClient.get<AdminPricebooksResponse>('/pricebooks/admin', { params }),

  create: (data: CreatePricebookRequest) =>
    apiClient.post<CreatePricebookResponse>('/pricebooks/', data),

  listCommercialAdmin: (params?: ListAdminCommercialPricebooksParams) =>
    apiClient.get<AdminCommercialPricebooksResponse>('/admin/pricebooks', {
      params,
    }),

  updateCommercialAdmin: (
    pricebookId: string,
    data: UpdateAdminPricebookRequest,
  ) =>
    apiClient.patch<AdminPricebookLifecycleResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookId)}`,
      data,
    ),

  publishCommercialAdmin: (
    pricebookId: string,
    data: PublishAdminPricebookRequest = {},
  ) =>
    apiClient.post<AdminPricebookLifecycleResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookId)}/publish`,
      data,
    ),

  scheduleCommercialAdmin: (
    pricebookId: string,
    data: ScheduleAdminPricebookRequest,
  ) =>
    apiClient.post<AdminPricebookLifecycleResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookId)}/schedule`,
      data,
    ),

  rollbackCommercialAdmin: (
    pricebookId: string,
    data: RollbackAdminPricebookRequest = {},
  ) =>
    apiClient.post<AdminPricebookLifecycleResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookId)}/rollback`,
      data,
    ),

  getCommercialHistory: (pricebookKey: string) =>
    apiClient.get<AdminPricebookHistoryResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookKey)}/history`,
    ),

  getCommercialAudit: (
    pricebookId: string,
    params?: AdminPricebookAuditParams,
  ) =>
    apiClient.get<AdminPricebookAuditResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookId)}/audit`,
      { params },
    ),

  validateCommercialAdmin: (pricebookId: string) =>
    apiClient.post<AdminPricebookValidationResponse>(
      `/admin/pricebooks/${encodeURIComponent(pricebookId)}/validate`,
    ),

  getCommercialContextOptions: () =>
    apiClient.get<CommercialContextOptionsResponse>(
      '/admin/commercial-context/options',
    ),

  updateCommercialContextOptions: (
    data: UpdateCommercialContextOptionsRequest,
  ) =>
    apiClient.put<CommercialContextOptionsResponse>(
      '/admin/commercial-context/options',
      data,
    ),
};
