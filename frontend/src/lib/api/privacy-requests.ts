import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';

export type PrivacyRequestType = 'account_deletion' | 'data_export';
export type PrivacyRequestStatus =
  | 'submitted'
  | 'identity_verification'
  | 'pending_decision'
  | 'approved'
  | 'scheduled'
  | 'fulfilled'
  | 'denied'
  | 'canceled'
  | 'failed';

export interface PrivacyRequestCreateRequest {
  request_type: PrivacyRequestType;
  reason_code?: string | null;
  reason?: string | null;
  notes?: string | null;
  feedback?: string | null;
  locale?: string | null;
}

export interface PrivacyRequestAcceptedResponse {
  privacy_request_reference: string;
  ticket_reference: string;
  request_type: PrivacyRequestType;
  status: PrivacyRequestStatus;
  message: string;
  submitted_at: string;
  manual_fulfillment_target_days: number;
  existing: boolean;
}

export interface PrivacyRequestSummary {
  privacy_request_reference: string;
  ticket_reference?: string | null;
  request_type: PrivacyRequestType;
  status: PrivacyRequestStatus;
  submitted_at: string;
  updated_at: string;
  scheduled_for?: string | null;
  fulfilled_at?: string | null;
  canceled_at?: string | null;
  manual_fulfillment_target_days: number;
  existing?: boolean;
  allowed_actions: string[];
}

export interface PrivacyRequestEvent {
  event_type: string;
  actor_type: 'customer' | 'admin' | 'system';
  from_status?: PrivacyRequestStatus | null;
  to_status?: PrivacyRequestStatus | null;
  safe_summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CustomerPrivacyRequestDetail extends PrivacyRequestSummary {
  reason_code?: string | null;
  notes_redacted?: string | null;
  events: PrivacyRequestEvent[];
}

export interface PrivacyRequestListResponse {
  requests: PrivacyRequestSummary[];
  next_cursor?: string | null;
}

export interface PrivacyRequestListParams {
  request_type?: PrivacyRequestType;
  status?: PrivacyRequestStatus;
  cursor?: string;
  limit?: number;
}

export const privacyRequestsApi = {
  create: (payload: PrivacyRequestCreateRequest, idempotencyKey: string) =>
    apiClient.post<PrivacyRequestAcceptedResponse>('/auth/me/privacy-requests', payload, {
      headers: {
        [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
      },
    }),

  list: (params?: PrivacyRequestListParams) =>
    apiClient.get<PrivacyRequestListResponse>('/auth/me/privacy-requests', { params }),

  get: (reference: string) =>
    apiClient.get<CustomerPrivacyRequestDetail>(
      `/auth/me/privacy-requests/${encodeURIComponent(reference)}`,
    ),

  cancel: (reference: string) =>
    apiClient.post<CustomerPrivacyRequestDetail>(
      `/auth/me/privacy-requests/${encodeURIComponent(reference)}/cancel`,
    ),
};
