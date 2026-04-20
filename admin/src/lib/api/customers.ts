import { apiClient } from './client';
import type { operations } from './generated/types';

type AdminMobileUsersListResponse =
  operations['list_mobile_users_api_v1_admin_mobile_users_get']['responses'][200]['content']['application/json'];
type AdminMobileUsersListParams =
  operations['list_mobile_users_api_v1_admin_mobile_users_get']['parameters']['query'];
type AdminMobileUserDetailResponse =
  operations['get_mobile_user_api_v1_admin_mobile_users__user_id__get']['responses'][200]['content']['application/json'];
type AdminUpdateMobileUserRequest =
  operations['update_mobile_user_api_v1_admin_mobile_users__user_id__patch']['requestBody']['content']['application/json'];
type AdminUpdateMobileUserResponse =
  operations['update_mobile_user_api_v1_admin_mobile_users__user_id__patch']['responses'][200]['content']['application/json'];
type AdminMobileUserSubscriptionSnapshotResponse =
  operations['get_mobile_user_subscription_snapshot_api_v1_admin_mobile_users__user_id__subscription_get']['responses'][200]['content']['application/json'];
type AdminCustomerStaffNotesParams =
  operations['list_customer_staff_notes_api_v1_admin_mobile_users__user_id__notes_get']['parameters']['query'];
type AdminCustomerStaffNotesResponse =
  operations['list_customer_staff_notes_api_v1_admin_mobile_users__user_id__notes_get']['responses'][200]['content']['application/json'];
type AdminCreateCustomerStaffNoteRequest =
  operations['create_customer_staff_note_api_v1_admin_mobile_users__user_id__notes_post']['requestBody']['content']['application/json'];
type AdminCreateCustomerStaffNoteResponse =
  operations['create_customer_staff_note_api_v1_admin_mobile_users__user_id__notes_post']['responses'][201]['content']['application/json'];
type AdminCustomerVpnUserResponse =
  operations['get_customer_vpn_user_api_v1_admin_mobile_users__user_id__vpn_user_get']['responses'][200]['content']['application/json'];
type AdminCustomerSupportActionRequest =
  operations['enable_customer_vpn_user_api_v1_admin_mobile_users__user_id__vpn_user_enable_post']['requestBody']['content']['application/json'];
type AdminRevokeCustomerDeviceResponse =
  operations['revoke_customer_device_api_v1_admin_mobile_users__user_id__devices__device_id__delete']['responses'][200]['content']['application/json'];
type AdminBulkDeviceRevokeResponse =
  operations['revoke_all_customer_devices_api_v1_admin_mobile_users__user_id__devices_revoke_all_post']['responses'][200]['content']['application/json'];
type AdminCustomerPasswordResetRequest =
  operations['reset_customer_password_api_v1_admin_mobile_users__user_id__credentials_reset_password_post']['requestBody']['content']['application/json'];
type AdminCustomerPasswordResetResponse =
  operations['reset_customer_password_api_v1_admin_mobile_users__user_id__credentials_reset_password_post']['responses'][200]['content']['application/json'];
type AdminCustomerSubscriptionResyncResponse =
  operations['resync_customer_subscription_api_v1_admin_mobile_users__user_id__subscription_resync_post']['responses'][200]['content']['application/json'];
type AdminCustomerTimelineParams =
  operations['get_customer_timeline_api_v1_admin_mobile_users__user_id__timeline_get']['parameters']['query'];
type AdminCustomerTimelineResponse =
  operations['get_customer_timeline_api_v1_admin_mobile_users__user_id__timeline_get']['responses'][200]['content']['application/json'];
type AdminCustomerOperationsInsightResponse =
  operations['get_customer_operations_insight_api_v1_admin_mobile_users__user_id__operations_insight_get']['responses'][200]['content']['application/json'];
type AdminCustomerOperationsActionRequest =
  operations['perform_customer_operations_action_api_v1_admin_mobile_users__user_id__operations_insight_actions_post']['requestBody']['content']['application/json'];
type AdminCustomerOperationsActionResponse =
  operations['perform_customer_operations_action_api_v1_admin_mobile_users__user_id__operations_insight_actions_post']['responses'][200]['content']['application/json'];
type AdminCustomerWorkspaceFinanceEvidenceResponse =
  operations['export_customer_workspace_finance_evidence_api_v1_admin_mobile_users__user_id__operations_insight_exports_workspaces__partner_account_id__get']['responses'][200]['content']['application/json'];
type AdminCustomerPartnerStatementEvidenceResponse =
  operations['export_customer_partner_statement_evidence_api_v1_admin_mobile_users__user_id__operations_insight_exports_partner_statements__statement_id__get']['responses'][200]['content']['application/json'];
type AdminCustomerPayoutInstructionEvidenceResponse =
  operations['export_customer_payout_instruction_evidence_api_v1_admin_mobile_users__user_id__operations_insight_exports_payout_instructions__payout_instruction_id__get']['responses'][200]['content']['application/json'];
type AdminCustomerPayoutExecutionEvidenceResponse =
  operations['export_customer_payout_execution_evidence_api_v1_admin_mobile_users__user_id__operations_insight_exports_payout_executions__payout_execution_id__get']['responses'][200]['content']['application/json'];

export interface AdminApiDownloadResult {
  blob: Blob;
  filename: string;
}

function resolveDownloadFilename(
  contentDisposition: string | undefined,
  fallback: string,
): string {
  if (!contentDisposition) {
    return fallback;
  }

  const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }

  const asciiMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
  if (asciiMatch?.[1]) {
    return asciiMatch[1];
  }

  return fallback;
}

async function downloadAdminEvidence(
  path: string,
  fallbackFilename: string,
): Promise<AdminApiDownloadResult> {
  const response = await apiClient.get<Blob>(path, { responseType: 'blob' });
  return {
    blob: response.data,
    filename: resolveDownloadFilename(
      response.headers['content-disposition'] as string | undefined,
      fallbackFilename,
    ),
  };
}

export const customersApi = {
  listMobileUsers: (params?: AdminMobileUsersListParams) =>
    apiClient.get<AdminMobileUsersListResponse>('/admin/mobile-users', { params }),

  getMobileUser: (userId: string) =>
    apiClient.get<AdminMobileUserDetailResponse>(`/admin/mobile-users/${userId}`),

  updateMobileUser: (userId: string, data: AdminUpdateMobileUserRequest) =>
    apiClient.patch<AdminUpdateMobileUserResponse>(`/admin/mobile-users/${userId}`, data),

  getSubscriptionSnapshot: (userId: string) =>
    apiClient.get<AdminMobileUserSubscriptionSnapshotResponse>(`/admin/mobile-users/${userId}/subscription`),

  listSupportNotes: (userId: string, params?: AdminCustomerStaffNotesParams) =>
    apiClient.get<AdminCustomerStaffNotesResponse>(`/admin/mobile-users/${userId}/notes`, { params }),

  createSupportNote: (userId: string, data: AdminCreateCustomerStaffNoteRequest) =>
    apiClient.post<AdminCreateCustomerStaffNoteResponse>(`/admin/mobile-users/${userId}/notes`, data),

  getVpnUser: (userId: string) =>
    apiClient.get<AdminCustomerVpnUserResponse>(`/admin/mobile-users/${userId}/vpn-user`),

  enableVpnUser: (userId: string, data: AdminCustomerSupportActionRequest = {}) =>
    apiClient.post<AdminCustomerVpnUserResponse>(`/admin/mobile-users/${userId}/vpn-user/enable`, data),

  disableVpnUser: (userId: string, data: AdminCustomerSupportActionRequest = {}) =>
    apiClient.post<AdminCustomerVpnUserResponse>(`/admin/mobile-users/${userId}/vpn-user/disable`, data),

  revokeDevice: (userId: string, deviceId: string) =>
    apiClient.delete<AdminRevokeCustomerDeviceResponse>(`/admin/mobile-users/${userId}/devices/${deviceId}`),

  revokeAllDevices: (userId: string, data: AdminCustomerSupportActionRequest = {}) =>
    apiClient.post<AdminBulkDeviceRevokeResponse>(`/admin/mobile-users/${userId}/devices/revoke-all`, data),

  resetPassword: (userId: string, data: AdminCustomerPasswordResetRequest) =>
    apiClient.post<AdminCustomerPasswordResetResponse>(`/admin/mobile-users/${userId}/credentials/reset-password`, data),

  resyncSubscription: (userId: string, data: AdminCustomerSupportActionRequest = {}) =>
    apiClient.post<AdminCustomerSubscriptionResyncResponse>(`/admin/mobile-users/${userId}/subscription/resync`, data),

  getTimeline: (userId: string, params?: AdminCustomerTimelineParams) =>
    apiClient.get<AdminCustomerTimelineResponse>(`/admin/mobile-users/${userId}/timeline`, { params }),

  getOperationsInsight: (userId: string) =>
    apiClient.get<AdminCustomerOperationsInsightResponse>(`/admin/mobile-users/${userId}/operations-insight`),

  performOperationsAction: (userId: string, data: AdminCustomerOperationsActionRequest) =>
    apiClient.post<AdminCustomerOperationsActionResponse>(`/admin/mobile-users/${userId}/operations-insight/actions`, data),

  downloadWorkspaceFinanceEvidence: (userId: string, partnerAccountId: string) =>
    downloadAdminEvidence(
      `/admin/mobile-users/${userId}/operations-insight/exports/workspaces/${partnerAccountId}`,
      `customer-operations-workspace-finance-evidence-${partnerAccountId}.json`,
    ),

  downloadPartnerStatementEvidence: (userId: string, statementId: string) =>
    downloadAdminEvidence(
      `/admin/mobile-users/${userId}/operations-insight/exports/partner-statements/${statementId}`,
      `customer-operations-partner-statement-evidence-${statementId}.json`,
    ),

  downloadPayoutInstructionEvidence: (userId: string, payoutInstructionId: string) =>
    downloadAdminEvidence(
      `/admin/mobile-users/${userId}/operations-insight/exports/payout-instructions/${payoutInstructionId}`,
      `customer-operations-payout-instruction-evidence-${payoutInstructionId}.json`,
    ),

  downloadPayoutExecutionEvidence: (userId: string, payoutExecutionId: string) =>
    downloadAdminEvidence(
      `/admin/mobile-users/${userId}/operations-insight/exports/payout-executions/${payoutExecutionId}`,
      `customer-operations-payout-execution-evidence-${payoutExecutionId}.json`,
    ),
};

export type {
  AdminCreateCustomerStaffNoteRequest,
  AdminCreateCustomerStaffNoteResponse,
  AdminCustomerPasswordResetRequest,
  AdminCustomerPasswordResetResponse,
  AdminCustomerStaffNotesParams,
  AdminCustomerStaffNotesResponse,
  AdminCustomerSubscriptionResyncResponse,
  AdminCustomerSupportActionRequest,
  AdminCustomerTimelineParams,
  AdminCustomerTimelineResponse,
  AdminCustomerVpnUserResponse,
  AdminCustomerOperationsInsightResponse,
  AdminCustomerOperationsActionRequest,
  AdminCustomerOperationsActionResponse,
  AdminCustomerPartnerStatementEvidenceResponse,
  AdminCustomerPayoutExecutionEvidenceResponse,
  AdminCustomerPayoutInstructionEvidenceResponse,
  AdminBulkDeviceRevokeResponse,
  AdminMobileUserDetailResponse,
  AdminMobileUserSubscriptionSnapshotResponse,
  AdminMobileUsersListParams,
  AdminMobileUsersListResponse,
  AdminCustomerWorkspaceFinanceEvidenceResponse,
  AdminRevokeCustomerDeviceResponse,
  AdminUpdateMobileUserRequest,
  AdminUpdateMobileUserResponse,
};
