import { CANONICAL_IDEMPOTENCY_HEADER, apiClient } from './client';

export const MESSAGING_CONVERSATION_STATUSES = [
  'open',
  'closed',
  'archived',
  'locked',
] as const;

export const MESSAGING_RESPONSE_STATES = [
  'none',
  'waiting_customer',
  'waiting_admin',
] as const;

export const MESSAGING_CONVERSATION_CATEGORIES = [
  'support',
  'billing',
  'subscription',
  'security',
  'system',
  'other',
] as const;

export const MESSAGING_PRIORITIES = [
  'low',
  'normal',
  'high',
  'urgent',
] as const;

export const NOTIFICATION_BROADCAST_AUDIENCE_TYPES = [
  'explicit_customers',
  'customer_segment',
  'all_customers',
  'admins',
] as const;

export type MessagingConversationStatus = (typeof MESSAGING_CONVERSATION_STATUSES)[number];
export type MessagingResponseState = (typeof MESSAGING_RESPONSE_STATES)[number];
export type MessagingConversationCategory = (typeof MESSAGING_CONVERSATION_CATEGORIES)[number];
export type MessagingPriority = (typeof MESSAGING_PRIORITIES)[number];
export type MessagingSenderType = 'customer' | 'admin' | 'system';
export type MessagingMessageVisibility = 'public' | 'internal';
export type MessagingBodyFormat = 'plain_text';
export type NotificationBroadcastAudienceType = (typeof NOTIFICATION_BROADCAST_AUDIENCE_TYPES)[number];
export type NotificationBroadcastCampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'sending'
  | 'sent'
  | 'cancelled'
  | 'failed';

export interface AdminMessagingConversationListParams {
  assigned_admin_id?: string;
  category?: MessagingConversationCategory;
  cursor?: string;
  customer_account_id?: string;
  limit?: number;
  priority?: MessagingPriority;
  query?: string;
  status?: MessagingConversationStatus;
}

export interface MessagingMessageWriteRequest {
  body: string;
  client_message_id?: string | null;
}

export interface AdminMessagingConversationCreateRequest {
  assigned_admin_id?: string | null;
  category: MessagingConversationCategory;
  customer_account_id: string;
  initial_message: MessagingMessageWriteRequest;
  priority: MessagingPriority;
  related_support_ticket_id?: string | null;
  subject: string;
}

export interface AdminMessagingConversationUpdateRequest {
  assigned_admin_id?: string | null;
  category?: MessagingConversationCategory;
  priority?: MessagingPriority;
}

export interface AdminMessagingConversationSummary {
  assigned_admin_id?: string | null;
  category: MessagingConversationCategory;
  closed_at?: string | null;
  created_at: string;
  created_by_admin_id?: string | null;
  customer_account_id: string;
  id: string;
  last_message_at?: string | null;
  priority: MessagingPriority;
  public_id: string;
  related_support_ticket_id?: string | null;
  response_state: MessagingResponseState;
  status: MessagingConversationStatus;
  subject: string;
  updated_at: string;
}

export interface AdminMessagingMessage {
  body: string;
  body_format: MessagingBodyFormat;
  client_message_id?: string | null;
  conversation_id: string;
  created_at: string;
  id: string;
  public_id: string;
  sender_id?: string | null;
  sender_type: MessagingSenderType;
  updated_at: string;
  visibility: MessagingMessageVisibility;
}

export interface AdminMessagingReadState {
  conversation_id: string;
  id: string;
  last_read_at: string;
  last_read_message_id?: string | null;
  participant_id: string;
  updated_at: string;
}

export interface AdminMessagingConversationDetail extends AdminMessagingConversationSummary {
  messages: AdminMessagingMessage[];
  read_states: AdminMessagingReadState[];
}

export interface AdminMessagingConversationListResponse {
  conversations: AdminMessagingConversationSummary[];
  nextCursor?: string | null;
  next_cursor?: string | null;
}

export interface AdminMessagingMessageWriteResponse {
  conversation: AdminMessagingConversationSummary;
  created: boolean;
  message: AdminMessagingMessage;
}

export interface AdminNotificationBroadcastCreateRequest {
  action_url?: string | null;
  audience_filter: Record<string, unknown>;
  audience_type: NotificationBroadcastAudienceType;
  body: string;
  name: string;
  scheduled_at?: string | null;
  title: string;
}

export interface AdminNotificationBroadcastCampaign {
  action_url?: string | null;
  audience_filter: Record<string, unknown>;
  audience_type: NotificationBroadcastAudienceType;
  body: string;
  created_at: string;
  created_by_admin_id: string;
  id: string;
  name: string;
  public_id: string;
  scheduled_at?: string | null;
  status: NotificationBroadcastCampaignStatus;
  title: string;
  updated_at: string;
}

function adminMessagingConversationPath(conversationRef: string) {
  return `/admin/messaging/conversations/${encodeURIComponent(conversationRef)}`;
}

function withIdempotency(clientMessageId: string) {
  return {
    headers: {
      [CANONICAL_IDEMPOTENCY_HEADER]: clientMessageId,
    },
  };
}

export const messagingApi = {
  listAdminConversations: (params?: AdminMessagingConversationListParams) =>
    apiClient.get<AdminMessagingConversationListResponse>(
      '/admin/messaging/conversations',
      { params },
    ),

  getAdminConversation: (conversationRef: string) =>
    apiClient.get<AdminMessagingConversationDetail>(
      adminMessagingConversationPath(conversationRef),
    ),

  createAdminConversation: (
    data: AdminMessagingConversationCreateRequest,
    clientMessageId: string,
  ) =>
    apiClient.post<AdminMessagingConversationDetail>(
      '/admin/messaging/conversations',
      data,
      withIdempotency(clientMessageId),
    ),

  addAdminMessage: (
    conversationRef: string,
    data: MessagingMessageWriteRequest,
    clientMessageId: string,
  ) =>
    apiClient.post<AdminMessagingMessageWriteResponse>(
      `${adminMessagingConversationPath(conversationRef)}/messages`,
      data,
      withIdempotency(clientMessageId),
    ),

  addAdminInternalNote: (
    conversationRef: string,
    data: MessagingMessageWriteRequest,
    clientMessageId: string,
  ) =>
    apiClient.post<AdminMessagingMessageWriteResponse>(
      `${adminMessagingConversationPath(conversationRef)}/internal-notes`,
      data,
      withIdempotency(clientMessageId),
    ),

  updateAdminConversation: (
    conversationRef: string,
    data: AdminMessagingConversationUpdateRequest,
  ) =>
    apiClient.patch<AdminMessagingConversationDetail>(
      adminMessagingConversationPath(conversationRef),
      data,
    ),

  closeAdminConversation: (conversationRef: string) =>
    apiClient.post<AdminMessagingConversationDetail>(
      `${adminMessagingConversationPath(conversationRef)}/close`,
    ),

  reopenAdminConversation: (conversationRef: string) =>
    apiClient.post<AdminMessagingConversationDetail>(
      `${adminMessagingConversationPath(conversationRef)}/reopen`,
    ),

  createAdminNotificationBroadcast: (data: AdminNotificationBroadcastCreateRequest) =>
    apiClient.post<AdminNotificationBroadcastCampaign>(
      '/admin/notifications/broadcasts',
      data,
    ),

  cancelAdminNotificationBroadcast: (campaignRef: string) =>
    apiClient.post<AdminNotificationBroadcastCampaign>(
      `/admin/notifications/broadcasts/${encodeURIComponent(campaignRef)}/cancel`,
    ),
};
