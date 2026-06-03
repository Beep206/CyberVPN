import { apiClient } from './client';
import type { operations } from './generated/types';

type ResolvePricebooksOperation =
  operations['resolve_pricebooks_api_v1_pricebooks_resolve_get'];
type ListAdminPricebooksOperation =
  operations['list_admin_pricebooks_api_v1_pricebooks_admin_get'];
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
type JsonObject = Record<string, unknown>;
type PricebookEntryResponse = {
  id: string;
  offer_id: string;
  visible_price: number;
  compare_at_price: number | null;
  included_addon_codes: string[];
  display_order: number;
};
type AdminPricebookRecordBase = {
  id: string;
  pricebook_key: string;
  display_name: string;
  storefront_id: string;
  merchant_profile_id: string | null;
  currency_code: string;
  region_code: string | null;
  discount_rules: JsonObject;
  renewal_pricing_policy: JsonObject;
  version_status: string;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  entries: PricebookEntryResponse[];
};
export type AdminCommercialPricebookRecord = AdminPricebookRecordBase & {
  lifecycle_status: string;
};
export type AdminCommercialPricebooksResponse =
  AdminCommercialPricebookRecord[];
export type ListAdminCommercialPricebooksParams = {
  include_inactive?: boolean;
  storefront_id?: string | null;
  storefront_key?: string | null;
  currency_code?: string | null;
  region_code?: string | null;
};
export type UpdateAdminPricebookRequest = Partial<
  Omit<AdminPricebookRecordBase, 'id' | 'pricebook_key' | 'entries'>
> & {
  entries?: PricebookEntryRequest[];
  change_reason?: string | null;
};
export type AdminPricebookLifecycleResponse = {
  pricebook: AdminPricebookRecordBase;
  lifecycle_status: string;
  audit_action: string;
};
export type PublishAdminPricebookRequest = {
  effective_from?: string | null;
  change_reason?: string | null;
};
export type ScheduleAdminPricebookRequest = {
  scheduled_for: string;
  change_reason?: string | null;
};
export type RollbackAdminPricebookRequest = {
  target_pricebook_id?: string | null;
  change_reason?: string | null;
};
export type AdminPricebookHistoryResponse = {
  pricebook_key: string;
  versions: AdminCommercialPricebookRecord[];
};
export type AdminPricebookAuditParams = {
  limit?: number;
};
export type AdminPricebookAuditResponse = Array<{
  id: string;
  admin_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  old_value: JsonObject | null;
  new_value: JsonObject | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}>;
export type AdminPricebookValidationResponse = {
  pricebook_id: string;
  valid: boolean;
  checked_at: string;
  issues: Array<{
    code:
      | 'missing_price'
      | 'unsupported_currency'
      | 'missing_provisioning_profile'
      | 'incompatible_addon';
    severity: 'error' | 'warning';
    message: string;
    field: string | null;
    entry_id: string | null;
    offer_id: string | null;
    remediation: string | null;
  }>;
};
export type CommercialContextCountryOption = {
  country_code: string;
  default_currency_code: string;
  supported_currency_codes: string[];
  payment_country_code: string | null;
  is_enabled: boolean;
};
export type CommercialContextCurrencyOption = {
  currency_code: string;
  minor_units: number;
  is_enabled: boolean;
};
export type CommercialContextOptionsResponse = {
  countries: CommercialContextCountryOption[];
  currencies: CommercialContextCurrencyOption[];
  source: 'default' | 'system_config';
};
export type UpdateCommercialContextOptionsRequest = {
  countries: CommercialContextCountryOption[];
  currencies: CommercialContextCurrencyOption[];
  change_reason?: string | null;
};
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
