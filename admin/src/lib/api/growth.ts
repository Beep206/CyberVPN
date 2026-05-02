import { apiClient } from './client';
import type { operations } from './generated/types';

type AdminListPromosResponse =
  operations['admin_list_promos_api_v1_admin_promo_codes_get']['responses'][200]['content']['application/json'];
type AdminCreatePromoRequest =
  operations['admin_create_promo_api_v1_admin_promo_codes_post']['requestBody']['content']['application/json'];
type AdminCreatePromoResponse =
  operations['admin_create_promo_api_v1_admin_promo_codes_post']['responses'][201]['content']['application/json'];
type AdminGetPromoResponse =
  operations['admin_get_promo_api_v1_admin_promo_codes__promo_id__get']['responses'][200]['content']['application/json'];
type AdminUpdatePromoRequest =
  operations['admin_update_promo_api_v1_admin_promo_codes__promo_id__put']['requestBody']['content']['application/json'];
type AdminUpdatePromoResponse =
  operations['admin_update_promo_api_v1_admin_promo_codes__promo_id__put']['responses'][200]['content']['application/json'];
type AdminDeactivatePromoResponse =
  operations['admin_deactivate_promo_api_v1_admin_promo_codes__promo_id__delete']['responses'][200]['content']['application/json'];
type AdminCreateInviteCodesRequest =
  operations['admin_create_invites_api_v1_admin_invite_codes_post']['requestBody']['content']['application/json'];
type AdminCreateInviteCodesResponse =
  operations['admin_create_invites_api_v1_admin_invite_codes_post']['responses'][201]['content']['application/json'];
type AdminPromotePartnerRequest =
  operations['admin_promote_partner_api_v1_admin_partners_promote_post']['requestBody']['content']['application/json'];
type AdminPromotePartnerResponse =
  operations['admin_promote_partner_api_v1_admin_partners_promote_post']['responses'][200]['content']['application/json'];
type AdminReferralOverviewResponse =
  operations['get_referral_overview_api_v1_admin_referrals_overview_get']['responses'][200]['content']['application/json'];
type AdminReferralUserDetailResponse =
  operations['get_referral_user_detail_api_v1_admin_referrals_users__user_id__get']['responses'][200]['content']['application/json'];
type AdminPartnersListResponse =
  operations['list_partners_api_v1_admin_partners_get']['responses'][200]['content']['application/json'];
type AdminPartnersListParams =
  operations['list_partners_api_v1_admin_partners_get']['parameters']['query'];
type AdminPartnerDetailResponse =
  operations['get_partner_detail_api_v1_admin_partners__user_id__get']['responses'][200]['content']['application/json'];
type AdminGrowthSignalsOverviewResponse =
  operations['get_growth_signals_overview_api_v1_admin_growth_signals_overview_get']['responses'][200]['content']['application/json'];
type AdminGrowthAbuseSignalsResponse =
  operations['list_growth_abuse_signals_api_v1_admin_growth_signals_abuse_queue_get']['responses'][200]['content']['application/json'];

export interface AdminGrowthCodeLookupRequest {
  code: string;
  action_context?: 'checkout' | 'redeem' | 'signup' | 'admin_lookup';
  lookup_user_id?: string | null;
  storefront_key?: string | null;
  plan_id?: string | null;
  amount?: number | null;
  channel?: string;
  existing_partner_code_present?: boolean;
  existing_promo_present?: boolean;
}

export interface AdminGrowthCodeLookupResponse {
  accepted: boolean;
  code_type: 'invite' | 'referral' | 'promo' | 'gift' | 'partner' | null;
  action_context: 'checkout' | 'redeem' | 'signup' | 'admin_lookup';
  result: 'accepted' | 'rejected' | 'conflicted' | 'blocked_by_risk';
  reject_reason?: string | null;
  conflict_code?: string | null;
  wrong_context_target?: 'checkout' | 'redeem' | null;
  issuer_type?: string | null;
  owner_type?: string | null;
  resolved_code_id?: string | null;
  growth_code_id?: string | null;
  promo_code_id?: string | null;
  partner_code_id?: string | null;
  user_message_key: string;
}

export interface AdminGrowthSignalCount {
  key: string;
  count: number;
}

export interface AdminGrowthLifecycleEvent {
  id: string;
  event_name: string;
  event_family: string;
  aggregate_type: string;
  aggregate_id: string;
  occurred_at: string;
  event_status: string;
}

export interface AdminGrowthSignalsOverview {
  total_codes: number;
  active_codes: number;
  total_redemptions: number;
  active_reservations: number;
  blocked_reward_count: number;
  available_referral_credit_usd: number;
  code_status_breakdown: AdminGrowthSignalCount[];
  resolution_result_breakdown: AdminGrowthSignalCount[];
  rejection_reason_breakdown: AdminGrowthSignalCount[];
  redemption_breakdown: AdminGrowthSignalCount[];
  reward_status_breakdown: AdminGrowthSignalCount[];
  reward_type_breakdown: AdminGrowthSignalCount[];
  recent_lifecycle_events: AdminGrowthLifecycleEvent[];
}

export interface AdminGrowthReportingFamilySummary {
  family: string;
  issued_total: number;
  resolution_attempts_total: number;
  resolution_accepted_total: number;
  resolution_rejected_total: number;
  redemption_total: number;
  reservations_reserved_total: number;
  reservations_consumed_total: number;
  reservations_released_total: number;
  reservations_expired_total: number;
  rewards_created_total: number;
  rewards_available_total: number;
  rewards_reversed_total: number;
  reward_created_amount_usd: number;
  reward_available_amount_usd: number;
  reward_reversed_amount_usd: number;
}

export interface AdminGrowthReportingDailyPoint extends AdminGrowthReportingFamilySummary {
  report_date: string;
}

export interface AdminGrowthReportingRefreshRun {
  id: string;
  trigger_kind: string;
  refresh_status: string;
  requested_window_days: number;
  window_start: string;
  window_end: string;
  latest_rollup_date?: string | null;
  rows_written: number;
  families_updated: string[];
  error_message?: string | null;
  started_at: string;
  finished_at: string;
  refreshed_at?: string | null;
}

export interface AdminGrowthReportingHealth {
  freshness_status: 'fresh' | 'stale' | 'failed' | 'never_refreshed' | string;
  stale_reason?: string | null;
  refresh_age_seconds?: number | null;
  expected_refresh_interval_seconds: number;
  stale_after_seconds: number;
  auto_refresh_enabled: boolean;
  latest_attempt_at?: string | null;
  latest_success_at?: string | null;
  latest_failure_at?: string | null;
  latest_failure_message?: string | null;
  latest_run?: AdminGrowthReportingRefreshRun | null;
}

export interface AdminGrowthReportingExecutiveSummary {
  total_issued: number;
  total_redemptions: number;
  total_reward_available_usd: number;
  total_reward_reversed_usd: number;
  resolution_acceptance_rate_pct: number;
  dominant_family?: string | null;
  highlights: string[];
}

export interface AdminGrowthReportingRecipientPolicy {
  template_key: string;
  template_locale: string;
  email_subject_prefix?: string | null;
  title_override?: string | null;
  recipient_domain_policy: string;
  allowed_recipient_domains: string[];
  suppressed_until?: string | null;
  suppression_reason_code?: string | null;
}

export interface AdminGrowthReportingGovernanceFollowup {
  status: string;
  reason_code?: string | null;
  opened_at?: string | null;
  due_at?: string | null;
  last_notified_at?: string | null;
  resolved_at?: string | null;
  resolution_code?: string | null;
  is_overdue: boolean;
  action_required: boolean;
}

export interface AdminGrowthReportingGovernanceCoverageCount {
  coverage_state: string;
  count: number;
}

export interface AdminGrowthReportingGovernanceFollowupQueueItem {
  subscription_id: string;
  recipient_email: string;
  audience_key: string;
  health_status: string;
  followup: AdminGrowthReportingGovernanceFollowup;
  next_delivery_at: string;
  latest_delivery_status?: string | null;
  latest_delivery_reason?: string | null;
}

export interface AdminGrowthReportingGovernanceDecision {
  delivery_id: string;
  subscription_id: string;
  recipient_email: string;
  audience_key: string;
  template_key: string;
  decision_kind: string;
  status_reason: string;
  created_at: string;
  planned_at: string;
  window_start: string;
  window_end: string;
  can_export_artifact: boolean;
  summary: string;
}

export interface AdminGrowthReportingGovernanceAuditEvent {
  id: string;
  action: string;
  entity_id?: string | null;
  actor_label: string;
  reason_code?: string | null;
  changed_fields: string[];
  created_at: string;
}

export interface AdminGrowthReportingGovernanceOverview {
  generated_at: string;
  active_subscription_count: number;
  paused_subscription_count: number;
  coverage_gap_count: number;
  followup_open_count: number;
  followup_overdue_count: number;
  coverage_counts: AdminGrowthReportingGovernanceCoverageCount[];
  followup_queue: AdminGrowthReportingGovernanceFollowupQueueItem[];
  recent_decisions: AdminGrowthReportingGovernanceDecision[];
  recent_audit_events: AdminGrowthReportingGovernanceAuditEvent[];
  notes: string[];
}

export interface AdminGrowthReportingOverview {
  window_start: string;
  window_end: string;
  latest_rollup_date?: string | null;
  refreshed_at?: string | null;
  family_summaries: AdminGrowthReportingFamilySummary[];
  daily_points: AdminGrowthReportingDailyPoint[];
  totals: AdminGrowthReportingFamilySummary;
  health: AdminGrowthReportingHealth;
  executive_summary: AdminGrowthReportingExecutiveSummary;
  coverage_notes: string[];
}

export interface AdminGrowthReportingRefreshResponse {
  trigger_kind: string;
  window_start: string;
  window_end: string;
  latest_rollup_date?: string | null;
  refreshed_at: string;
  rows_written: number;
  families_updated: string[];
  coverage_notes: string[];
}

export interface AdminGrowthReportingSubscription {
  id: string;
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  delivery_channel: string;
  cadence: string;
  report_window_days: number;
  subscription_status: string;
  next_delivery_at: string;
  last_delivery_attempt_at?: string | null;
  last_success_at?: string | null;
  latest_delivery_status?: string | null;
  latest_delivery_reason?: string | null;
  health_status: string;
  policy: AdminGrowthReportingRecipientPolicy;
  followup: AdminGrowthReportingGovernanceFollowup;
}

export interface AdminGrowthReportingDelivery {
  id: string;
  subscription_id: string;
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  delivery_channel: string;
  cadence: string;
  report_window_days: number;
  template_key: string;
  template_locale: string;
  subject_line: string;
  title_line: string;
  delivery_status: string;
  status_reason?: string | null;
  freshness_status: string;
  artifact_checksum?: string | null;
  provider_name?: string | null;
  provider_message_id?: string | null;
  failure_message?: string | null;
  window_start: string;
  window_end: string;
  planned_at: string;
  started_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
  updated_at: string;
  can_export_artifact: boolean;
  policy: AdminGrowthReportingRecipientPolicy;
}

export interface AdminGrowthReportingSubscriptionsResponse {
  items: AdminGrowthReportingSubscription[];
  total: number;
  overdue_count: number;
  active_count: number;
  retention_rollup_days: number;
  retention_refresh_run_days: number;
  retention_delivery_days: number;
}

export interface AdminGrowthReportingDeliveriesResponse {
  items: AdminGrowthReportingDelivery[];
  total: number;
  failed_count: number;
}

export interface AdminGrowthReportingGovernanceExportResponse {
  export_kind: string;
  filename: string;
  exported_at: string;
  overview: AdminGrowthReportingGovernanceOverview;
  payload: Record<string, unknown>;
}

export interface AdminCreateGrowthReportingSubscriptionRequest {
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  cadence: string;
  report_window_days: number;
  policy?: AdminGrowthReportingRecipientPolicyRequest;
}

export interface AdminGrowthReportingRecipientPolicyRequest {
  template_key?: string | null;
  template_locale?: string;
  email_subject_prefix?: string | null;
  title_override?: string | null;
  recipient_domain_policy?: string;
  allowed_recipient_domains?: string[];
  suppressed_until?: string | null;
  suppression_reason_code?: string | null;
}

export interface AdminUpdateGrowthReportingSubscriptionRequest {
  recipient_email: string;
  recipient_name?: string | null;
  audience_key: string;
  cadence: string;
  report_window_days: number;
  policy?: AdminGrowthReportingRecipientPolicyRequest;
  reason_code?: string | null;
}

export interface AdminUpdateGrowthReportingSubscriptionStatusRequest {
  reason_code?: string | null;
}

export interface AdminUpdateGrowthReportingGovernanceFollowupRequest {
  reason_code?: string | null;
}

export interface AdminGrowthAbuseSignal {
  signal_key: string;
  signal_type: string;
  severity: string;
  code_type?: string | null;
  reason_code: string;
  count: number;
  unique_users: number;
  latest_event_at: string;
  review_hint: string;
  growth_code_id?: string | null;
  reward_allocation_id?: string | null;
  beneficiary_user_id?: string | null;
  source_redemption_id?: string | null;
}

export interface AdminGrowthAbuseSignals {
  items: AdminGrowthAbuseSignal[];
  total: number;
}

export interface AdminGrowthNotificationDelivery {
  id: string;
  mobile_user_id: string;
  user?: {
    id: string;
    email: string;
    username?: string | null;
    telegram_username?: string | null;
    referral_code?: string | null;
    is_partner: boolean;
  } | null;
  notification_key: string;
  notification_kind: string;
  delivery_channel: string;
  delivery_status: string;
  status_reason?: string | null;
  title: string;
  message: string;
  route_slug?: string | null;
  notes: string[];
  source_kind?: string | null;
  source_id?: string | null;
  notification_queue_id?: string | null;
  queue_status?: string | null;
  queue_error_message?: string | null;
  created_by_admin_user_id?: string | null;
  planned_at: string;
  delivered_at?: string | null;
  created_at: string;
  updated_at: string;
  can_resend: boolean;
  can_pause: boolean;
  can_revoke: boolean;
  can_resolve: boolean;
}

export interface AdminGrowthNotificationQueueSnapshot {
  id: string;
  status: string;
  attempts: number;
  scheduled_at: string;
  sent_at?: string | null;
  error_message?: string | null;
}

export interface AdminGrowthNotificationDeliveryEvent {
  id: string;
  event_type: string;
  delivery_status: string;
  reason_code?: string | null;
  event_payload: Record<string, unknown>;
  event_note?: string | null;
  notification_queue_id?: string | null;
  created_by_admin_user_id?: string | null;
  occurred_at: string;
  created_at: string;
}

export interface AdminGrowthNotificationSourceSummary {
  source_kind: string;
  source_id?: string | null;
  source_label?: string | null;
  source_status?: string | null;
  owner_user_id?: string | null;
  beneficiary_user_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface AdminGrowthNotificationDeliveryDetail {
  delivery: AdminGrowthNotificationDelivery;
  sibling_deliveries: AdminGrowthNotificationDelivery[];
  event_timeline: AdminGrowthNotificationDeliveryEvent[];
  queue_snapshot?: AdminGrowthNotificationQueueSnapshot | null;
  source_summary?: AdminGrowthNotificationSourceSummary | null;
  lifecycle_events: AdminGrowthLifecycleEvent[];
  troubleshooting_state: string;
  customer_message_key: string;
  support_summary: string;
}

export interface AdminListGrowthNotificationDeliveriesResponse {
  items: AdminGrowthNotificationDelivery[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminListGrowthNotificationDeliveriesParams {
  mobile_user_id?: string;
  delivery_channel?: string;
  delivery_status?: string;
  source_kind?: string;
  offset?: number;
  limit?: number;
}

export interface AdminGrowthNotificationDeliveryActionRequest {
  reason_code?: string | null;
}

export interface AdminManualGrowthNotificationRequest {
  mobile_user_id: string;
  title: string;
  message: string;
  route_slug?: string;
  locale?: string;
  notes?: string[];
  channels?: string[];
}

export interface AdminManualGrowthNotificationResponse {
  deliveries: AdminGrowthNotificationDelivery[];
}

export interface AdminGiftCodeListItem {
  id: string;
  masked_code: string;
  raw_code?: string | null;
  batch_id?: string | null;
  status: string;
  issuer_type: string;
  source_type?: string | null;
  owner_user_id?: string | null;
  issued_by_admin_id?: string | null;
  plan_family?: string | null;
  duration_days?: number | null;
  recipient_hint?: string | null;
  gift_message?: string | null;
  expires_at?: string | null;
  created_at: string;
  redeemed_at?: string | null;
  redeemed_by_user_id?: string | null;
  source_order_id?: string | null;
  source_payment_id?: string | null;
}

export interface AdminListGiftCodesResponse {
  items: AdminGiftCodeListItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface AdminListGiftCodesParams {
  owner_user_id?: string;
  offset?: number;
  limit?: number;
}

export interface AdminIssueGiftCodeRequest {
  owner_user_id: string;
  plan_id: string;
  recipient_hint?: string | null;
  gift_message?: string | null;
  reason_code?: string | null;
  admin_note?: string | null;
}

export interface AdminIssueGiftCodeResponse {
  gift_code: AdminGiftCodeListItem;
}

export interface AdminIssueGiftCodeBatchRequest {
  owner_user_id: string;
  plan_id: string;
  count: number;
  recipient_hint?: string | null;
  gift_message?: string | null;
  reason_code?: string | null;
  admin_note?: string | null;
}

export interface AdminIssueGiftCodeBatchResponse {
  batch_id: string;
  issued_count: number;
  gift_codes: AdminGiftCodeListItem[];
}

export interface AdminPartnerWorkspaceMemberResponse {
  id: string;
  admin_user_id: string;
  role_id: string;
  role_key: string;
  role_display_name: string;
  membership_status: string;
  permission_keys: string[];
  invited_by_admin_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminPartnerWorkspaceResponse {
  id: string;
  account_key: string;
  display_name: string;
  status: string;
  legacy_owner_user_id: string | null;
  created_by_admin_user_id: string | null;
  code_count: number;
  active_code_count: number;
  total_clients: number;
  total_earned: number;
  last_activity_at: string | null;
  current_role_key: string | null;
  current_permission_keys: string[];
  members: AdminPartnerWorkspaceMemberResponse[];
}

export interface AdminCreatePartnerWorkspaceRequest {
  display_name: string;
  account_key?: string | null;
  legacy_owner_user_id?: string | null;
  owner_admin_user_id?: string | null;
}

/**
 * Growth API client
 * Covers admin-ready acquisition and promotion surfaces.
 */
export const growthApi = {
  listPromos: (params?: { offset?: number; limit?: number }) =>
    apiClient.get<AdminListPromosResponse>('/admin/promo-codes', { params }),

  createPromo: (data: AdminCreatePromoRequest) =>
    apiClient.post<AdminCreatePromoResponse>('/admin/promo-codes', data),

  getPromo: (promoId: string) =>
    apiClient.get<AdminGetPromoResponse>(`/admin/promo-codes/${promoId}`),

  updatePromo: (promoId: string, data: AdminUpdatePromoRequest) =>
    apiClient.put<AdminUpdatePromoResponse>(`/admin/promo-codes/${promoId}`, data),

  deactivatePromo: (promoId: string) =>
    apiClient.delete<AdminDeactivatePromoResponse>(`/admin/promo-codes/${promoId}`),

  createInviteCodes: (data: AdminCreateInviteCodesRequest) =>
    apiClient.post<AdminCreateInviteCodesResponse>('/admin/invite-codes', data),

  promotePartner: (data: AdminPromotePartnerRequest) =>
    apiClient.post<AdminPromotePartnerResponse>('/admin/partners/promote', data),

  getReferralOverview: () =>
    apiClient.get<AdminReferralOverviewResponse>('/admin/referrals/overview'),

  getReferralUserDetail: (userId: string) =>
    apiClient.get<AdminReferralUserDetailResponse>(`/admin/referrals/users/${userId}`),

  listPartners: (params?: AdminPartnersListParams) =>
    apiClient.get<AdminPartnersListResponse>('/admin/partners', { params }),

  getPartnerDetail: (userId: string) =>
    apiClient.get<AdminPartnerDetailResponse>(`/admin/partners/${userId}`),

  getGrowthSignalsOverview: () =>
    apiClient.get<AdminGrowthSignalsOverviewResponse>('/admin/growth-signals/overview'),

  getGrowthReportingOverview: (params?: { window_days?: number }) =>
    apiClient.get<AdminGrowthReportingOverview>('/admin/growth-reporting/overview', { params }),

  getGrowthReportingGovernanceOverview: () =>
    apiClient.get<AdminGrowthReportingGovernanceOverview>('/admin/growth-reporting/governance'),

  refreshGrowthReporting: (params?: { window_days?: number }) =>
    apiClient.post<AdminGrowthReportingRefreshResponse>('/admin/growth-reporting/refresh', undefined, { params }),

  listGrowthReportingSubscriptions: () =>
    apiClient.get<AdminGrowthReportingSubscriptionsResponse>('/admin/growth-reporting/subscriptions'),

  createGrowthReportingSubscription: (data: AdminCreateGrowthReportingSubscriptionRequest) =>
    apiClient.post<AdminGrowthReportingSubscription>('/admin/growth-reporting/subscriptions', data),

  updateGrowthReportingSubscription: (
    subscriptionId: string,
    data: AdminUpdateGrowthReportingSubscriptionRequest,
  ) =>
    apiClient.put<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}`,
      data,
    ),

  pauseGrowthReportingSubscription: (
    subscriptionId: string,
    data: AdminUpdateGrowthReportingSubscriptionStatusRequest = {},
  ) =>
    apiClient.post<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}/pause`,
      data,
    ),

  resumeGrowthReportingSubscription: (
    subscriptionId: string,
    data: AdminUpdateGrowthReportingSubscriptionStatusRequest = {},
  ) =>
    apiClient.post<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}/resume`,
      data,
    ),

  updateGrowthReportingGovernanceFollowup: (
    subscriptionId: string,
    action: 'resolve' | 'dismiss',
    data: AdminUpdateGrowthReportingGovernanceFollowupRequest = {},
  ) =>
    apiClient.post<AdminGrowthReportingSubscription>(
      `/admin/growth-reporting/subscriptions/${subscriptionId}/follow-up/${action}`,
      data,
    ),

  listGrowthReportingDeliveries: (params?: { limit?: number }) =>
    apiClient.get<AdminGrowthReportingDeliveriesResponse>('/admin/growth-reporting/deliveries', { params }),

  exportGrowthReportingOverview: async (params?: { window_days?: number }) => {
    const response = await apiClient.get<Blob>('/admin/growth-reporting/export', {
      params,
      responseType: 'blob',
    });
    return response;
  },

  exportGrowthReportingGovernanceSnapshot: async () => {
    const response = await apiClient.get<Blob>('/admin/growth-reporting/governance/export', {
      responseType: 'blob',
    });
    return response;
  },

  exportGrowthReportingDeliveryArtifact: async (deliveryId: string) => {
    const response = await apiClient.get<Blob>(
      `/admin/growth-reporting/deliveries/${deliveryId}/artifact`,
      { responseType: 'blob' },
    );
    return response;
  },

  listGrowthAbuseSignals: (params?: { limit?: number }) =>
    apiClient.get<AdminGrowthAbuseSignalsResponse>('/admin/growth-signals/abuse-queue', { params }),

  listGrowthNotificationDeliveries: (params?: AdminListGrowthNotificationDeliveriesParams) =>
    apiClient.get<AdminListGrowthNotificationDeliveriesResponse>(
      '/admin/growth-notification-deliveries',
      { params },
    ),

  getGrowthNotificationDeliveryDetail: (deliveryId: string) =>
    apiClient.get<AdminGrowthNotificationDeliveryDetail>(
      `/admin/growth-notification-deliveries/${deliveryId}`,
    ),

  exportGrowthNotificationDeliveryDetail: async (deliveryId: string) => {
    const response = await apiClient.get<Blob>(
      `/admin/growth-notification-deliveries/${deliveryId}/export`,
      { responseType: 'blob' },
    );
    return response;
  },

  createManualGrowthNotification: (data: AdminManualGrowthNotificationRequest) =>
    apiClient.post<AdminManualGrowthNotificationResponse>(
      '/admin/growth-notification-deliveries/manual',
      data,
    ),

  resendGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/resend`,
      data,
    ),

  pauseGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/pause`,
      data,
    ),

  revokeGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/revoke`,
      data,
    ),

  resolveGrowthNotificationDelivery: (
    deliveryId: string,
    data: AdminGrowthNotificationDeliveryActionRequest = {},
  ) =>
    apiClient.post<AdminGrowthNotificationDelivery>(
      `/admin/growth-notification-deliveries/${deliveryId}/resolve`,
      data,
    ),

  lookupGrowthCode: (data: AdminGrowthCodeLookupRequest) =>
    apiClient.post<AdminGrowthCodeLookupResponse>('/admin/growth-codes/lookup', data),

  listGiftCodes: (params?: AdminListGiftCodesParams) =>
    apiClient.get<AdminListGiftCodesResponse>('/admin/gift-codes', { params }),

  issueGiftCode: (data: AdminIssueGiftCodeRequest) =>
    apiClient.post<AdminIssueGiftCodeResponse>('/admin/gift-codes/issue', data),

  issueGiftCodeBatch: (data: AdminIssueGiftCodeBatchRequest) =>
    apiClient.post<AdminIssueGiftCodeBatchResponse>('/admin/gift-code-batches/issue', data),

  createPartnerWorkspace: (data: AdminCreatePartnerWorkspaceRequest) =>
    apiClient.post<AdminPartnerWorkspaceResponse>('/admin/partner-workspaces', data),

  getPartnerWorkspace: (workspaceId: string) =>
    apiClient.get<AdminPartnerWorkspaceResponse>(`/admin/partner-workspaces/${workspaceId}`),
};

export type {
  AdminGrowthAbuseSignalsResponse,
  AdminGrowthSignalsOverviewResponse,
  AdminCreateInviteCodesRequest,
  AdminCreateInviteCodesResponse,
  AdminPartnerDetailResponse,
  AdminPartnersListParams,
  AdminPartnersListResponse,
  AdminCreatePromoRequest,
  AdminCreatePromoResponse,
  AdminDeactivatePromoResponse,
  AdminGetPromoResponse,
  AdminListPromosResponse,
  AdminPromotePartnerRequest,
  AdminPromotePartnerResponse,
  AdminReferralOverviewResponse,
  AdminReferralUserDetailResponse,
  AdminUpdatePromoRequest,
  AdminUpdatePromoResponse,
};
