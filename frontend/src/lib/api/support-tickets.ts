import { apiClient } from './client';

export type SupportTicketCategory =
  | 'account'
  | 'billing'
  | 'setup'
  | 'vpn_access'
  | 'status'
  | 'privacy'
  | 'other';

export type SupportTicketPriority = 'high' | 'low' | 'normal' | 'urgent';

export type SupportTicketStatus =
  | 'open'
  | 'pending_support'
  | 'pending_customer'
  | 'resolved'
  | 'closed';

export type PublicSupportActorLabel = 'customer' | 'partner' | 'support' | 'system';

export interface SupportTicketMessage {
  author_label: PublicSupportActorLabel;
  body: string;
  created_at: string;
}

export interface SupportTicketEvent {
  actor_label: PublicSupportActorLabel;
  event_type: string;
  from_value?: string | null;
  to_value?: string | null;
  audit_summary: string;
  created_at: string;
}

export interface SupportTicketSummary {
  public_id: string;
  status: SupportTicketStatus;
  category: SupportTicketCategory;
  priority: SupportTicketPriority;
  subject: string;
  last_message_preview: string;
  assigned_admin_id?: string | null;
  created_at: string;
  updated_at: string;
  last_customer_message_at?: string | null;
  last_support_message_at?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
}

export interface SupportTicketDetail extends SupportTicketSummary {
  messages: SupportTicketMessage[];
  events: SupportTicketEvent[];
}

export interface SupportTicketListResponse {
  tickets: SupportTicketSummary[];
  nextCursor?: string | null;
}

export interface SupportTicketListParams {
  category?: SupportTicketCategory;
  cursor?: string;
  limit?: number;
  status?: SupportTicketStatus;
}

export interface SupportTicketCreateRequest {
  category: SupportTicketCategory;
  message: string;
  priority?: SupportTicketPriority;
  subject: string;
}

export interface SupportTicketReplyRequest {
  message: string;
}

export const supportTicketsApi = {
  list: (params?: SupportTicketListParams) =>
    apiClient.get<SupportTicketListResponse>('/support/tickets', { params }),

  create: (payload: SupportTicketCreateRequest) =>
    apiClient.post<SupportTicketDetail>('/support/tickets', payload),

  get: (ticketRef: string) =>
    apiClient.get<SupportTicketDetail>(`/support/tickets/${ticketRef}`),

  reply: (ticketRef: string, payload: SupportTicketReplyRequest) =>
    apiClient.post<SupportTicketDetail>(
      `/support/tickets/${ticketRef}/replies`,
      payload,
    ),

  close: (ticketRef: string) =>
    apiClient.post<SupportTicketDetail>(`/support/tickets/${ticketRef}/close`, {}),

  reopen: (ticketRef: string) =>
    apiClient.post<SupportTicketDetail>(`/support/tickets/${ticketRef}/reopen`, {}),
};
