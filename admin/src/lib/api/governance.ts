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

type MiniAppRuntimeRollout = {
  enabled: boolean;
  mode: 'live' | 'canary' | 'maintenance' | 'rollback';
  trial_enabled: boolean;
  checkout_enabled: boolean;
  config_enabled: boolean;
  maintenance_message: string | null;
  canary_telegram_user_ids: number[];
};

type MiniAppRuntimeConfigResponse = {
  key: string;
  rollout: MiniAppRuntimeRollout;
  description: string | null;
  updated_at: string | null;
  updated_by: string | null;
};

type UpdateMiniAppRuntimeConfigRequest = MiniAppRuntimeRollout & {
  change_reason?: string | null;
};

type MiniAppLaunchReadiness = {
  observability_acknowledged: boolean;
  incident_runbook_acknowledged: boolean;
  checkout_canary_passed: boolean;
  config_delivery_canary_passed: boolean;
  rollback_drill_acknowledged: boolean;
  support_window_confirmed: boolean;
  customer_comms_ready: boolean;
  status_page_template_ready: boolean;
  incident_channel: string | null;
  rollback_commander: string | null;
  primary_oncall_contact: string | null;
  release_window_note: string | null;
  is_ready: boolean;
};

type MiniAppLaunchReadinessConfigResponse = {
  key: string;
  readiness: MiniAppLaunchReadiness;
  description: string | null;
  updated_at: string | null;
  updated_by: string | null;
};

type UpdateMiniAppLaunchReadinessConfigRequest = Omit<MiniAppLaunchReadiness, 'is_ready'> & {
  change_reason?: string | null;
};

type MiniAppLaunchSummaryResponse = {
  launch_state:
    | 'live'
    | 'ready_for_live'
    | 'canary_in_progress'
    | 'rollback_in_progress'
    | 'maintenance'
    | 'blocked';
  live_switch_allowed: boolean;
  next_action:
    | 'promote_to_live'
    | 'complete_launch_gates'
    | 'keep_canary'
    | 'finish_rollback'
    | 'hold_maintenance'
    | 'stabilize_runtime';
  primary_action:
    | 'promote_to_live'
    | 'enter_maintenance'
    | 'start_rollback'
    | 'return_to_canary'
    | null;
  available_actions: Array<
    'promote_to_live'
    | 'enter_maintenance'
    | 'start_rollback'
    | 'return_to_canary'
  >;
  blockers: string[];
  runtime: MiniAppRuntimeRollout;
  readiness: MiniAppLaunchReadiness;
};

type ExecuteMiniAppLaunchActionRequest = {
  action:
    | 'promote_to_live'
    | 'enter_maintenance'
    | 'start_rollback'
    | 'return_to_canary';
  change_reason?: string | null;
};

type MiniAppLaunchTimelineEntry = {
  id: string;
  created_at: string;
  admin_id: string | null;
  action: string;
  event_type: 'runtime_update' | 'launch_readiness_update' | 'launch_action';
  action_name:
    | 'promote_to_live'
    | 'enter_maintenance'
    | 'start_rollback'
    | 'return_to_canary'
    | null;
  resulting_runtime_mode: 'live' | 'canary' | 'maintenance' | 'rollback' | null;
  resulting_launch_state:
    | 'live'
    | 'ready_for_live'
    | 'canary_in_progress'
    | 'rollback_in_progress'
    | 'maintenance'
    | 'blocked'
    | null;
  readiness_ready: boolean | null;
  change_reason: string | null;
  entity_id: string | null;
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

  getMiniAppRuntimeConfig: () =>
    apiClient.get<MiniAppRuntimeConfigResponse>('/admin/system-config/miniapp-runtime'),

  updateMiniAppRuntimeConfig: (data: UpdateMiniAppRuntimeConfigRequest) =>
    apiClient.put<MiniAppRuntimeConfigResponse>('/admin/system-config/miniapp-runtime', data),

  getMiniAppLaunchReadinessConfig: () =>
    apiClient.get<MiniAppLaunchReadinessConfigResponse>('/admin/system-config/miniapp-launch-readiness'),

  updateMiniAppLaunchReadinessConfig: (data: UpdateMiniAppLaunchReadinessConfigRequest) =>
    apiClient.put<MiniAppLaunchReadinessConfigResponse>('/admin/system-config/miniapp-launch-readiness', data),

  getMiniAppLaunchSummary: () =>
    apiClient.get<MiniAppLaunchSummaryResponse>('/admin/system-config/miniapp-launch-summary'),

  executeMiniAppLaunchAction: (data: ExecuteMiniAppLaunchActionRequest) =>
    apiClient.post<MiniAppLaunchSummaryResponse>('/admin/system-config/miniapp-launch-actions', data),

  getMiniAppLaunchTimeline: (params?: { limit?: number }) =>
    apiClient.get<MiniAppLaunchTimelineEntry[]>('/admin/system-config/miniapp-launch-timeline', { params }),

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
