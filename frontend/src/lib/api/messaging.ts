import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from './client';

export type MessagingConversationStatus = 'open' | 'closed' | 'archived' | 'locked';
export type MessagingResponseState = 'none' | 'waiting_customer' | 'waiting_admin';
export type MessagingConversationCategory =
  | 'support'
  | 'billing'
  | 'subscription'
  | 'security'
  | 'system'
  | 'other';
export type MessagingPriority = 'low' | 'normal' | 'high' | 'urgent';
export type MessagingSenderType = 'customer' | 'admin' | 'system';
export type MessagingMessageVisibility = 'public' | 'internal';
export type MessagingBodyFormat = 'plain_text';
export type SiteNotificationType =
  | 'message'
  | 'system'
  | 'billing'
  | 'subscription'
  | 'security'
  | 'broadcast';
export type SiteNotificationSeverity = 'info' | 'success' | 'warning' | 'critical';
export type SiteNotificationDeliveryStatus =
  | 'pending'
  | 'delivered'
  | 'read'
  | 'dismissed'
  | 'failed'
  | 'expired';

export interface CustomerMessagingMessage {
  id: string;
  public_id: string;
  conversation_id: string;
  sender_type: MessagingSenderType;
  visibility: MessagingMessageVisibility;
  body: string;
  created_at: string;
}

export interface CustomerConversationSummary {
  id: string;
  public_id: string;
  status: MessagingConversationStatus;
  response_state: MessagingResponseState;
  category: MessagingConversationCategory;
  priority: MessagingPriority;
  subject: string;
  unread_count: number;
  created_at: string;
  updated_at: string;
  last_message_at?: string | null;
  closed_at?: string | null;
}

export interface CustomerConversationDetail extends CustomerConversationSummary {
  messages: CustomerMessagingMessage[];
}

export interface CustomerConversationListResponse {
  conversations: CustomerConversationSummary[];
  nextCursor?: string | null;
}

export interface CustomerConversationListParams {
  cursor?: string;
  limit?: number;
  status?: MessagingConversationStatus;
}

export interface CustomerMessagingWriteRequest {
  body: string;
  client_message_id?: string | null;
}

export interface CustomerMessagingWriteResponse {
  message: CustomerMessagingMessage;
  conversation: CustomerConversationSummary;
  created: boolean;
}

export interface MessagingReadStateResponse {
  id: string;
  conversation_id: string;
  participant_id: string;
  last_read_message_id?: string | null;
  last_read_at: string;
  updated_at: string;
}

export interface SiteNotification {
  id: string;
  delivery_id: string;
  notification_type: SiteNotificationType;
  severity: SiteNotificationSeverity;
  title: string;
  body?: string | null;
  action_url?: string | null;
  aggregate_type?: string | null;
  aggregate_id?: string | null;
  conversation_id?: string | null;
  message_id?: string | null;
  status: SiteNotificationDeliveryStatus;
  created_at: string;
  updated_at: string;
  read_at?: string | null;
}

export interface SiteNotificationListResponse {
  notifications: SiteNotification[];
  nextCursor?: string | null;
}

export interface SiteNotificationReadRequest {
  notification_ids?: string[];
  read_all_before?: string | null;
}

export interface SiteNotificationReadResponse {
  notifications: SiteNotification[];
}

export interface SiteNotificationDismissRequest {
  notification_ids?: string[];
  read_all_before?: string | null;
}

export interface SiteNotificationDismissResponse {
  notifications: SiteNotification[];
}

export interface MessagingUnreadCounts {
  conversations: number;
  notifications: number;
}

export interface MessagingRealtimeSyncResponse {
  cursor: string;
  conversations: CustomerConversationSummary[];
  messages: CustomerMessagingMessage[];
  notifications: SiteNotification[];
  unread_counts: MessagingUnreadCounts;
}

export interface MessagingRealtimeTicketResponse {
  ticket: string;
  expiresIn: number;
}

export interface MessagingRealtimeEvent {
  event_id?: string;
  channel?: string;
  cursor?: string;
  event_type?: string;
  payload?: {
    conversation_id?: string;
    message_id?: string;
    notification_id?: string;
  };
  sync_cursor?: string;
  type?: string;
}

export function isCustomerVisibleMessage(
  message: CustomerMessagingMessage,
): boolean {
  return message.visibility === 'public';
}

export const messagingApi = {
  listConversations: (params?: CustomerConversationListParams) =>
    apiClient.get<CustomerConversationListResponse>('/me/conversations', {
      params,
    }),

  getConversation: (conversationRef: string) =>
    apiClient.get<CustomerConversationDetail>(
      `/me/conversations/${conversationRef}`,
    ),

  replyToConversation: (
    conversationRef: string,
    payload: CustomerMessagingWriteRequest,
    idempotencyKey: string,
  ) =>
    apiClient.post<CustomerMessagingWriteResponse>(
      `/me/conversations/${conversationRef}/messages`,
      payload,
      {
        headers: {
          [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
        },
      },
    ),

  markConversationRead: (
    conversationRef: string,
    payload: { last_read_message_id?: string | null },
  ) =>
    apiClient.post<MessagingReadStateResponse>(
      `/me/conversations/${conversationRef}/read`,
      payload,
    ),

  listNotifications: (params?: { cursor?: string; limit?: number }) =>
    apiClient.get<SiteNotificationListResponse>('/me/notifications', {
      params,
    }),

  markNotificationsRead: (payload: SiteNotificationReadRequest) =>
    apiClient.post<SiteNotificationReadResponse>(
      '/me/notifications/read',
      payload,
    ),

  dismissNotifications: (payload: SiteNotificationDismissRequest) =>
    apiClient.post<SiteNotificationDismissResponse>(
      '/me/notifications/dismiss',
      payload,
    ),

  getRealtimeTicket: () =>
    apiClient.post<MessagingRealtimeTicketResponse>('/me/realtime/ticket', {}),

  syncRealtime: (params?: { cursor?: string | null; limit?: number }) =>
    apiClient.get<MessagingRealtimeSyncResponse>('/me/realtime/sync', {
      params,
    }),
};
