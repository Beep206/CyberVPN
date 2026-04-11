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
};
