import { apiClient } from './client';

export const PRIVACY_REQUEST_STATUSES = [
  'submitted',
  'identity_verification',
  'pending_decision',
  'approved',
  'scheduled',
  'fulfilled',
  'denied',
  'canceled',
  'failed',
] as const;

export const PRIVACY_REQUEST_TYPES = ['account_deletion', 'data_export'] as const;

export type PrivacyRequestStatus = (typeof PRIVACY_REQUEST_STATUSES)[number];
export type PrivacyRequestType = (typeof PRIVACY_REQUEST_TYPES)[number];
export type PrivacyRequestActorType = 'customer' | 'admin' | 'system';

export interface AdminPrivacyRequestListParams {
  assigned_admin_id?: string;
  cursor?: string;
  limit?: number;
  overdue?: boolean;
  query?: string;
  request_type?: PrivacyRequestType;
  status?: PrivacyRequestStatus;
  submitted_from?: string;
  submitted_to?: string;
}

export interface PrivacyRequestEvent {
  actor_type: PrivacyRequestActorType;
  created_at: string;
  event_type: string;
  from_status?: PrivacyRequestStatus | null;
  metadata: Record<string, unknown>;
  safe_summary: string;
  to_status?: PrivacyRequestStatus | null;
}

export interface AdminPrivacyRequestSummary {
  allowed_actions: string[];
  assigned_admin_id?: string | null;
  canceled_at?: string | null;
  existing?: boolean;
  fulfilled_at?: string | null;
  manual_fulfillment_target_days: number;
  overdue: boolean;
  privacy_request_reference: string;
  request_type: PrivacyRequestType;
  safe_customer_reference: string;
  scheduled_for?: string | null;
  status: PrivacyRequestStatus;
  submitted_at: string;
  ticket_reference?: string | null;
  updated_at: string;
}

export interface AdminPrivacyRequestDetail extends AdminPrivacyRequestSummary {
  customer_account_public_uid?: number | null;
  decision_at?: string | null;
  decision_reason?: string | null;
  events: PrivacyRequestEvent[];
  identity_verified_at?: string | null;
  last_error_code?: string | null;
  last_error_redacted?: string | null;
  notes_redacted?: string | null;
  policy_snapshot: Record<string, unknown>;
  principal_subject: string;
  reason_code?: string | null;
  review_started_at?: string | null;
  support_ticket_reference?: string | null;
  version: number;
}

export interface AdminPrivacyRequestListResponse {
  next_cursor?: string | null;
  requests: AdminPrivacyRequestSummary[];
}

export interface QueueCountResponse {
  count: number;
}

function adminPrivacyRequestPath(reference: string) {
  return `/admin/privacy-requests/${encodeURIComponent(reference)}`;
}

export const adminPrivacyRequestsApi = {
  list: (params?: AdminPrivacyRequestListParams) =>
    apiClient.get<AdminPrivacyRequestListResponse>('/admin/privacy-requests', { params }),

  countQueue: () =>
    apiClient.get<QueueCountResponse>('/admin/privacy-requests/queue-count'),

  get: (reference: string) =>
    apiClient.get<AdminPrivacyRequestDetail>(adminPrivacyRequestPath(reference)),

  startReview: (reference: string, assignToSelf = true) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/start-review`,
      { assign_to_self: assignToSelf },
    ),

  requestIdentityVerification: (reference: string, message: string) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/request-identity-verification`,
      { message },
    ),

  verifyIdentity: (reference: string, verificationMethod: string, safeNote?: string | null) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/verify-identity`,
      { safe_note: safeNote ?? null, verification_method: verificationMethod },
    ),

  approve: (reference: string, decisionReason: string) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/approve`,
      { decision_reason: decisionReason },
    ),

  deny: (reference: string, decisionReason: string) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/deny`,
      { decision_reason: decisionReason },
    ),

  schedule: (reference: string, scheduledFor?: string | null) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/schedule`,
      { scheduled_for: scheduledFor ?? null },
    ),

  execute: (reference: string, confirmText: string, stepUpToken?: string | null) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/execute`,
      { confirm_text: confirmText, step_up_token: stepUpToken ?? null },
    ),

  retry: (reference: string, scheduledFor?: string | null) =>
    apiClient.post<AdminPrivacyRequestDetail>(
      `${adminPrivacyRequestPath(reference)}/retry`,
      { scheduled_for: scheduledFor ?? null },
    ),
};
