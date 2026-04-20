import { apiClient } from './client';
import type { operations } from './generated/types';

type AuditLogsResponse =
  operations['get_audit_logs_api_v1_admin_audit_log_get']['responses'][200]['content']['application/json'];
type WebhookLogsResponse =
  operations['get_webhook_logs_api_v1_admin_webhook_log_get']['responses'][200]['content']['application/json'];
type ListAdminInvitesResponse =
  operations['list_invites_api_v1_admin_invites_get']['responses'][200]['content']['application/json'];
type CreateAdminInviteRequest =
  operations['create_invite_api_v1_admin_invites_post']['requestBody']['content']['application/json'];
type CreateAdminInviteResponse =
  operations['create_invite_api_v1_admin_invites_post']['responses'][201]['content']['application/json'];
type SettingsResponse =
  operations['get_settings_api_v1_settings__get']['responses'][200]['content']['application/json'];
type CreateSettingRequest =
  operations['create_setting_api_v1_settings__post']['requestBody']['content']['application/json'];
type CreateSettingResponse =
  operations['create_setting_api_v1_settings__post']['responses'][200]['content']['application/json'];
type UpdateSettingRequest =
  operations['update_setting_api_v1_settings__id__put']['requestBody']['content']['application/json'];
type UpdateSettingResponse =
  operations['update_setting_api_v1_settings__id__put']['responses'][200]['content']['application/json'];

type PolicyVersionResponse = {
  id: string;
  policy_family: string;
  policy_key: string;
  subject_type: string;
  subject_id: string | null;
  version_number: number;
  payload: Record<string, unknown>;
  approval_state: string;
  version_status: string;
  effective_from: string;
  effective_to: string | null;
  created_by_admin_user_id: string | null;
  approved_by_admin_user_id: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  supersedes_policy_version_id: string | null;
};

type CreatePolicyVersionRequest = {
  policy_family: string;
  policy_key: string;
  subject_type: string;
  subject_id?: string | null;
  version_number: number;
  payload?: Record<string, unknown>;
  approval_state?: string;
  version_status?: string;
  effective_from?: string | null;
  effective_to?: string | null;
  rejection_reason?: string | null;
  supersedes_policy_version_id?: string | null;
};

type ApprovePolicyVersionRequest = {
  version_status?: string;
  effective_from?: string | null;
  effective_to?: string | null;
};

type LegalDocumentResponse = {
  id: string;
  document_key: string;
  document_type: string;
  locale: string;
  title: string;
  content_markdown: string;
  content_checksum: string;
  policy_version_id: string;
  created_at: string;
  updated_at: string;
};

type CreateLegalDocumentRequest = {
  document_key: string;
  document_type: string;
  locale: string;
  title: string;
  content_markdown: string;
  policy_version_id: string;
};

type LegalDocumentSetItem = {
  id?: string;
  legal_document_id: string;
  required: boolean;
  display_order: number;
};

type LegalDocumentSetResponse = {
  id: string;
  set_key: string;
  storefront_id: string;
  auth_realm_id: string | null;
  display_name: string;
  policy_version_id: string;
  documents: LegalDocumentSetItem[];
  created_at: string;
  updated_at: string;
};

type CreateLegalDocumentSetRequest = {
  set_key: string;
  storefront_id: string;
  auth_realm_id?: string | null;
  display_name: string;
  policy_version_id: string;
  documents: LegalDocumentSetItem[];
};

export const governanceApi = {
  getAuditLogs: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<AuditLogsResponse>('/admin/audit-log', { params }),

  getWebhookLogs: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<WebhookLogsResponse>('/admin/webhook-log', { params }),

  listAdminInvites: () =>
    apiClient.get<ListAdminInvitesResponse>('/admin/invites'),

  createAdminInvite: (data: CreateAdminInviteRequest) =>
    apiClient.post<CreateAdminInviteResponse>('/admin/invites', data),

  revokeAdminInvite: (token: string) =>
    apiClient.delete(`/admin/invites/${token}`),

  getSettings: () =>
    apiClient.get<SettingsResponse>('/settings/'),

  createSetting: (data: CreateSettingRequest) =>
    apiClient.post<CreateSettingResponse>('/settings/', data),

  updateSetting: (id: number, data: UpdateSettingRequest) =>
    apiClient.put<UpdateSettingResponse>(`/settings/${id}`, data),

  listPolicyVersions: (params?: {
    policy_family?: string;
    policy_key?: string;
    include_inactive?: boolean;
  }) => apiClient.get<PolicyVersionResponse[]>('/policies/', { params }),

  createPolicyVersion: (data: CreatePolicyVersionRequest) =>
    apiClient.post<PolicyVersionResponse>('/policies/', data),

  approvePolicyVersion: (id: string, data: ApprovePolicyVersionRequest = {}) =>
    apiClient.post<PolicyVersionResponse>(`/policies/${id}/approve`, data),

  listLegalDocuments: (params?: { document_type?: string; locale?: string }) =>
    apiClient.get<LegalDocumentResponse[]>('/legal-documents/', { params }),

  createLegalDocument: (data: CreateLegalDocumentRequest) =>
    apiClient.post<LegalDocumentResponse>('/legal-documents/', data),

  createLegalDocumentSet: (data: CreateLegalDocumentSetRequest) =>
    apiClient.post<LegalDocumentSetResponse>('/legal-documents/sets', data),
};
