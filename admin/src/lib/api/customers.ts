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
  AdminBulkDeviceRevokeResponse,
  AdminMobileUserDetailResponse,
  AdminMobileUserSubscriptionSnapshotResponse,
  AdminMobileUsersListParams,
  AdminMobileUsersListResponse,
  AdminRevokeCustomerDeviceResponse,
  AdminUpdateMobileUserRequest,
  AdminUpdateMobileUserResponse,
};
