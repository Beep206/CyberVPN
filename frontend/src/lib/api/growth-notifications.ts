import { apiClient } from './client';

export interface GrowthNotificationItem {
  id: string;
  kind: string;
  tone: string;
  route_slug: string;
  title: string;
  message: string;
  notes: string[];
  action_required: boolean;
  unread: boolean;
  created_at: string;
  archived_at?: string | null;
  source_kind?: string | null;
  source_id?: string | null;
}

export interface GrowthNotificationCounters {
  total_notifications: number;
  unread_notifications: number;
  action_required_notifications: number;
}

export interface GrowthNotificationReadState {
  notification_id: string;
  read_at?: string | null;
  archived_at?: string | null;
}

export interface GrowthNotificationPreferences {
  growth_in_app_invites: boolean;
  growth_email_invites: boolean;
  growth_telegram_invites: boolean;
  growth_in_app_referral_rewards: boolean;
  growth_email_referral_rewards: boolean;
  growth_telegram_referral_rewards: boolean;
  growth_in_app_gifts: boolean;
  growth_email_gifts: boolean;
  growth_telegram_gifts: boolean;
  growth_in_app_admin_updates: boolean;
  growth_email_admin_updates: boolean;
  growth_telegram_admin_updates: boolean;
}

export type UpdateGrowthNotificationPreferencesRequest = Partial<GrowthNotificationPreferences>;

export interface GrowthNotificationDeliveryEvent {
  event_type: string;
  occurred_at?: string | null;
  summary: string;
}

export interface GrowthNotificationRepairTarget {
  kind: string;
  summary: string;
}

export interface GrowthNotificationDeliveryDetail {
  delivery_id: string;
  delivery_channel: 'in_app' | 'email' | 'telegram' | string;
  delivery_status: string;
  troubleshooting_state: string;
  customer_message_key: string;
  customer_summary: string;
  recovery_allowed: boolean;
  support_required: boolean;
  repair_target?: GrowthNotificationRepairTarget | null;
  planned_at: string;
  delivered_at?: string | null;
  events: GrowthNotificationDeliveryEvent[];
}

export interface GrowthNotificationSupportHandoff {
  reference_code: string;
  troubleshooting_summary: string;
  copy_text: string;
  suggested_escalation_channel: 'contact_form' | 'support_email' | 'telegram_support' | string;
  contact_subject: string;
  contact_body: string;
}

export interface GrowthNotificationDetail {
  notification: GrowthNotificationItem;
  deliveries: GrowthNotificationDeliveryDetail[];
  support_handoff: GrowthNotificationSupportHandoff;
}

export const growthNotificationsApi = {
  list: (includeArchived = false) =>
    apiClient.get<GrowthNotificationItem[]>('/growth-notifications', {
      params: includeArchived ? { include_archived: true } : undefined,
    }),

  getCounters: () =>
    apiClient.get<GrowthNotificationCounters>('/growth-notifications/counters'),

  markRead: (notificationId: string) =>
    apiClient.post<GrowthNotificationReadState>(`/growth-notifications/${notificationId}/read`),

  archive: (notificationId: string) =>
    apiClient.post<GrowthNotificationReadState>(`/growth-notifications/${notificationId}/archive`),

  getDetail: (notificationId: string) =>
    apiClient.get<GrowthNotificationDetail>(`/growth-notifications/${notificationId}`),

  requestRecovery: (notificationId: string, payload: { delivery_channel: string }) =>
    apiClient.post<GrowthNotificationDetail>(
      `/growth-notifications/${notificationId}/recovery`,
      payload,
    ),

  requestSupportEscalation: (
    notificationId: string,
    payload: { delivery_channel?: string | null; escalation_channel: string },
  ) =>
    apiClient.post<GrowthNotificationDetail>(
      `/growth-notifications/${notificationId}/support-escalation`,
      payload,
    ),

  getPreferences: () =>
    apiClient.get<GrowthNotificationPreferences>('/growth-notifications/preferences'),

  updatePreferences: (payload: UpdateGrowthNotificationPreferencesRequest) =>
    apiClient.patch<GrowthNotificationPreferences>('/growth-notifications/preferences', payload),
};
