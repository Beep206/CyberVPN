import { apiClient } from './client';

export const SUPPORT_TICKET_STATUSES = [
  'open',
  'pending_support',
  'pending_customer',
  'resolved',
  'closed',
] as const;

export const SUPPORT_TICKET_CATEGORIES = [
  'account',
  'billing',
  'setup',
  'vpn_access',
  'status',
  'privacy',
  'other',
  'abuse_review',
  'duplicate',
] as const;

export const SUPPORT_TICKET_PRIORITIES = [
  'low',
  'normal',
  'high',
  'urgent',
] as const;

export const SUPPORT_TICKET_SOURCES = [
  'customer_web',
  'telegram_mini_app',
  'partner_portal',
  'admin_manual',
  'telegram_bot',
] as const;

export type SupportTicketStatus = (typeof SUPPORT_TICKET_STATUSES)[number];
export type SupportTicketCategory = (typeof SUPPORT_TICKET_CATEGORIES)[number];
export type SupportTicketPriority = (typeof SUPPORT_TICKET_PRIORITIES)[number];
export type SupportTicketSource = (typeof SUPPORT_TICKET_SOURCES)[number];
export type SupportTicketOwnerType = 'customer' | 'partner';
export type SupportActorType = 'customer' | 'partner' | 'admin' | 'system';
export type SupportMessageVisibility = 'public' | 'internal';
export type SupportTicketEventType =
  | 'ticket_created'
  | 'public_reply_added'
  | 'internal_note_added'
  | 'status_changed'
  | 'priority_changed'
  | 'category_changed'
  | 'assigned'
  | 'closed'
  | 'reopened'
  | 'notification_queued'
  | 'notification_failed';

export interface AdminSupportTicketListParams {
  assigned_admin_id?: string;
  category?: SupportTicketCategory;
  cursor?: string;
  limit?: number;
  priority?: SupportTicketPriority;
  query?: string;
  source?: SupportTicketSource;
  status?: SupportTicketStatus;
}

export interface SupportTicketSummary {
  assigned_admin_id?: string | null;
  category: SupportTicketCategory;
  closed_at?: string | null;
  created_at: string;
  customer_account_id?: string | null;
  id: string;
  last_customer_message_at?: string | null;
  last_message_preview: string;
  last_support_message_at?: string | null;
  owner_type: SupportTicketOwnerType;
  partner_workspace_id?: string | null;
  priority: SupportTicketPriority;
  public_id: string;
  resolved_at?: string | null;
  source: SupportTicketSource;
  status: SupportTicketStatus;
  subject: string;
  updated_at: string;
}

export interface SupportTicketMessage {
  author_id?: string | null;
  author_type: SupportActorType;
  body: string;
  created_at: string;
  id: string;
  ticket_id: string;
  visibility: SupportMessageVisibility;
}

export interface SupportTicketEvent {
  actor_id?: string | null;
  actor_type: SupportActorType;
  audit_summary: string;
  created_at: string;
  event_type: SupportTicketEventType;
  from_value?: string | null;
  id: string;
  ticket_id: string;
  to_value?: string | null;
}

export interface SupportTicketDetail extends SupportTicketSummary {
  events: SupportTicketEvent[];
  messages: SupportTicketMessage[];
}

export interface SupportTicketListResponse {
  nextCursor?: string | null;
  next_cursor?: string | null;
  tickets: SupportTicketSummary[];
}

export interface SupportTicketReplyRequest {
  message: string;
}

export interface AdminSupportTicketUpdateRequest {
  assigned_admin_id?: string | null;
  category?: SupportTicketCategory;
  priority?: SupportTicketPriority;
  status?: SupportTicketStatus;
}

function adminSupportTicketPath(ticketRef: string) {
  return `/admin/support/tickets/${encodeURIComponent(ticketRef)}`;
}

export const supportApi = {
  listAdminTickets: (params?: AdminSupportTicketListParams) =>
    apiClient.get<SupportTicketListResponse>('/admin/support/tickets', { params }),

  getAdminTicket: (ticketRef: string) =>
    apiClient.get<SupportTicketDetail>(adminSupportTicketPath(ticketRef)),

  addAdminReply: (ticketRef: string, data: SupportTicketReplyRequest) =>
    apiClient.post<SupportTicketDetail>(
      `${adminSupportTicketPath(ticketRef)}/replies`,
      data,
    ),

  addAdminInternalNote: (ticketRef: string, data: SupportTicketReplyRequest) =>
    apiClient.post<SupportTicketDetail>(
      `${adminSupportTicketPath(ticketRef)}/internal-notes`,
      data,
    ),

  updateAdminTicket: (ticketRef: string, data: AdminSupportTicketUpdateRequest) =>
    apiClient.patch<SupportTicketDetail>(adminSupportTicketPath(ticketRef), data),
};
