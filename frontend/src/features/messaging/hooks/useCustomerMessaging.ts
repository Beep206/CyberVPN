'use client';

import { useEffect, useRef, useState } from 'react';
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query';
import {
  isCustomerVisibleMessage,
  messagingApi,
  type CustomerConversationDetail,
  type CustomerConversationListParams,
  type CustomerConversationListResponse,
  type CustomerConversationSummary,
  type CustomerMessagingMessage,
  type MessagingRealtimeEvent,
  type MessagingRealtimeSyncResponse,
  type MessagingUnreadCounts,
  type SiteNotification,
  type SiteNotificationListResponse,
} from '@/lib/api/messaging';

export type CustomerMessagingRealtimeStatus =
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'syncing'
  | 'offline'
  | 'unavailable';

const CUSTOMER_MESSAGING_SSE_EVENTS = [
  'messaging.conversation.created',
  'messaging.message.created',
  'messaging.message.read',
  'messaging.conversation.assigned',
  'messaging.conversation.closed',
  'messaging.conversation.reopened',
  'notification.created',
  'notification.read',
  'notification.dismissed',
  'sync_required',
] as const;

export const customerMessagingKeys = {
  all: ['customer-messaging'] as const,
  conversationDetails: () =>
    [...customerMessagingKeys.all, 'conversations', 'detail'] as const,
  conversationDetail: (conversationRef: string | null) =>
    [
      ...customerMessagingKeys.conversationDetails(),
      conversationRef ?? 'none',
    ] as const,
  conversationLists: () =>
    [...customerMessagingKeys.all, 'conversations', 'list'] as const,
  conversationList: (params: CustomerConversationListParams) =>
    [
      ...customerMessagingKeys.conversationLists(),
      params.status ?? 'all',
      params.cursor ?? 'first',
      params.limit ?? 50,
    ] as const,
  notificationLists: () =>
    [...customerMessagingKeys.all, 'notifications', 'list'] as const,
  notificationList: (params: { cursor?: string; limit?: number }) =>
    [
      ...customerMessagingKeys.notificationLists(),
      params.cursor ?? 'first',
      params.limit ?? 20,
    ] as const,
  unreadCounts: () =>
    [...customerMessagingKeys.all, 'unread-counts'] as const,
};

function mergeConversations(
  current: CustomerConversationSummary[],
  incoming: CustomerConversationSummary[],
): CustomerConversationSummary[] {
  const byId = new Map(current.map((conversation) => [conversation.id, conversation]));

  for (const conversation of incoming) {
    byId.set(conversation.id, conversation);
  }

  return Array.from(byId.values()).sort((left, right) => {
    const leftTime = left.last_message_at ?? left.updated_at ?? left.created_at;
    const rightTime = right.last_message_at ?? right.updated_at ?? right.created_at;

    return rightTime.localeCompare(leftTime);
  });
}

function mergeMessages(
  current: CustomerMessagingMessage[],
  incoming: CustomerMessagingMessage[],
): CustomerMessagingMessage[] {
  const byId = new Map(current.map((message) => [message.id, message]));

  for (const message of incoming.filter(isCustomerVisibleMessage)) {
    byId.set(message.id, message);
  }

  return Array.from(byId.values()).sort((left, right) =>
    left.created_at.localeCompare(right.created_at),
  );
}

function mergeNotifications(
  current: SiteNotification[],
  incoming: SiteNotification[],
): SiteNotification[] {
  const byId = new Map(current.map((notification) => [notification.id, notification]));

  for (const notification of incoming) {
    if (notification.status === 'dismissed') {
      byId.delete(notification.id);
    } else {
      byId.set(notification.id, notification);
    }
  }

  return Array.from(byId.values()).sort((left, right) =>
    right.created_at.localeCompare(left.created_at),
  );
}

export function mergeConversationListResponse(
  current: CustomerConversationListResponse | undefined,
  incoming: CustomerConversationSummary[],
): CustomerConversationListResponse | undefined {
  if (!current && incoming.length === 0) {
    return current;
  }

  return {
    conversations: mergeConversations(current?.conversations ?? [], incoming),
    nextCursor: current?.nextCursor ?? null,
  };
}

export function mergeNotificationListResponse(
  current: SiteNotificationListResponse | undefined,
  incoming: SiteNotification[],
): SiteNotificationListResponse | undefined {
  if (!current && incoming.length === 0) {
    return current;
  }

  return {
    notifications: mergeNotifications(current?.notifications ?? [], incoming),
    nextCursor: current?.nextCursor ?? null,
  };
}

export function updateMessagingCachesFromSync(
  queryClient: QueryClient,
  sync: MessagingRealtimeSyncResponse,
): void {
  queryClient.setQueriesData<CustomerConversationListResponse>(
    { queryKey: customerMessagingKeys.conversationLists() },
    (current) => mergeConversationListResponse(current, sync.conversations),
  );

  queryClient.setQueriesData<CustomerConversationDetail>(
    { queryKey: customerMessagingKeys.conversationDetails() },
    (current) => {
      if (!current) {
        return current;
      }

      const messagesForConversation = sync.messages.filter(
        (message) => message.conversation_id === current.id,
      );
      const summary = sync.conversations.find(
        (conversation) => conversation.id === current.id,
      );

      if (!summary && messagesForConversation.length === 0) {
        return current;
      }

      return {
        ...current,
        ...summary,
        messages: mergeMessages(current.messages, messagesForConversation),
      };
    },
  );

  queryClient.setQueriesData<SiteNotificationListResponse>(
    { queryKey: customerMessagingKeys.notificationLists() },
    (current) => mergeNotificationListResponse(current, sync.notifications),
  );

  queryClient.setQueryData<MessagingUnreadCounts>(
    customerMessagingKeys.unreadCounts(),
    sync.unread_counts,
  );
}

export function createCustomerMessageClientId(): string {
  const cryptoApi = globalThis.crypto;
  const rawId =
    cryptoApi && typeof cryptoApi.randomUUID === 'function'
      ? cryptoApi.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  return `web_${rawId.replace(/[^a-zA-Z0-9]/g, '').slice(0, 60)}`;
}

export function isUnreadSiteNotification(notification: SiteNotification): boolean {
  return !['dismissed', 'expired', 'read'].includes(notification.status);
}

export function useCustomerConversationList(
  params: CustomerConversationListParams = { limit: 50 },
) {
  return useQuery({
    queryKey: customerMessagingKeys.conversationList(params),
    queryFn: async () => {
      const { data } = await messagingApi.listConversations(params);
      return data;
    },
    staleTime: 30_000,
  });
}

export function useCustomerConversationDetail(conversationRef: string | null) {
  return useQuery({
    enabled: Boolean(conversationRef),
    queryKey: customerMessagingKeys.conversationDetail(conversationRef),
    queryFn: async () => {
      if (!conversationRef) {
        throw new Error('Customer conversation reference is required');
      }

      const { data } = await messagingApi.getConversation(conversationRef);

      return {
        ...data,
        messages: data.messages.filter(isCustomerVisibleMessage),
      };
    },
    staleTime: 15_000,
  });
}

export function useReplyCustomerConversation(conversationRef: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ body }: { body: string }) => {
      if (!conversationRef) {
        throw new Error('Customer conversation reference is required');
      }

      const clientMessageId = createCustomerMessageClientId();
      const { data } = await messagingApi.replyToConversation(
        conversationRef,
        {
          body,
          client_message_id: clientMessageId,
        },
        `customer-message:${conversationRef}:${clientMessageId}`,
      );

      return data;
    },
    onSuccess: async (result) => {
      const detailKey = customerMessagingKeys.conversationDetail(conversationRef);

      queryClient.setQueryData<CustomerConversationDetail>(detailKey, (current) => {
        if (!current) {
          return current;
        }

        return {
          ...current,
          ...result.conversation,
          messages: mergeMessages(current.messages, [result.message]),
        };
      });

      queryClient.setQueriesData<CustomerConversationListResponse>(
        { queryKey: customerMessagingKeys.conversationLists() },
        (current) => mergeConversationListResponse(current, [result.conversation]),
      );

      await queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.unreadCounts(),
      });
    },
  });
}

export function useMarkCustomerConversationRead(conversationRef: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (lastReadMessageId: string | null) => {
      if (!conversationRef) {
        throw new Error('Customer conversation reference is required');
      }

      const { data } = await messagingApi.markConversationRead(
        conversationRef,
        {
          last_read_message_id: lastReadMessageId,
        },
      );

      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: customerMessagingKeys.conversationLists(),
        }),
        queryClient.invalidateQueries({
          queryKey: customerMessagingKeys.unreadCounts(),
        }),
      ]);
    },
  });
}

export function useCustomerNotifications(params: { cursor?: string; limit?: number } = { limit: 20 }) {
  return useQuery({
    queryKey: customerMessagingKeys.notificationList(params),
    queryFn: async () => {
      const { data } = await messagingApi.listNotifications(params);
      return data;
    },
    staleTime: 30_000,
  });
}

export function useMarkCustomerNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificationIds: string[]) => {
      const { data } = await messagingApi.markNotificationsRead({
        notification_ids: notificationIds,
      });

      return data;
    },
    onSuccess: async (result) => {
      queryClient.setQueriesData<SiteNotificationListResponse>(
        { queryKey: customerMessagingKeys.notificationLists() },
        (current) => mergeNotificationListResponse(current, result.notifications),
      );

      await queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.unreadCounts(),
      });
    },
  });
}

export function useDismissCustomerNotifications() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificationIds: string[]) => {
      const { data } = await messagingApi.dismissNotifications({
        notification_ids: notificationIds,
      });

      return data;
    },
    onSuccess: async (result) => {
      queryClient.setQueriesData<SiteNotificationListResponse>(
        { queryKey: customerMessagingKeys.notificationLists() },
        (current) => mergeNotificationListResponse(current, result.notifications),
      );

      await queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.unreadCounts(),
      });
    },
  });
}

function parseRealtimeEvent(rawData: string): MessagingRealtimeEvent | null {
  try {
    const parsed = JSON.parse(rawData) as unknown;
    return parsed && typeof parsed === 'object'
      ? (parsed as MessagingRealtimeEvent)
      : null;
  } catch {
    return null;
  }
}

function shouldRefreshForRealtimeEvent(event: MessagingRealtimeEvent): boolean {
  return Boolean(
    event.event_type?.startsWith('messaging.') ||
      event.event_type?.startsWith('notification.') ||
      event.type === 'sync_required',
  );
}

export function useCustomerMessagingRealtimeSession({ enabled = true } = {}) {
  const queryClient = useQueryClient();
  const cursorRef = useRef<string | null>(null);
  const recoveryInFlightRef = useRef(false);
  const [status, setStatus] = useState<CustomerMessagingRealtimeStatus>(
    enabled ? 'connecting' : 'unavailable',
  );
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      setStatus('unavailable');
      return;
    }

    if (typeof window === 'undefined') {
      setStatus('unavailable');
      return;
    }

    let cancelled = false;

    const invalidateRealtimeQueries = async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: customerMessagingKeys.conversationLists(),
        }),
        queryClient.invalidateQueries({
          queryKey: customerMessagingKeys.conversationDetails(),
        }),
        queryClient.invalidateQueries({
          queryKey: customerMessagingKeys.notificationLists(),
        }),
        queryClient.invalidateQueries({
          queryKey: customerMessagingKeys.unreadCounts(),
        }),
      ]);
    };

    const recoverFromRest = async () => {
      if (recoveryInFlightRef.current) {
        return;
      }

      recoveryInFlightRef.current = true;
      setStatus(navigator.onLine === false ? 'offline' : 'syncing');

      try {
        const { data } = await messagingApi.syncRealtime({
          cursor: cursorRef.current,
          limit: 100,
        });

        if (cancelled) {
          return;
        }

        cursorRef.current = data.cursor;
        updateMessagingCachesFromSync(queryClient, data);
        await invalidateRealtimeQueries();
        setLastSyncedAt(new Date().toISOString());
        setStatus('connected');
      } catch {
        if (!cancelled) {
          setStatus(navigator.onLine === false ? 'offline' : 'reconnecting');
        }
      } finally {
        recoveryInFlightRef.current = false;
      }
    };

    const handleRealtimeMessage = (event: MessageEvent<string>) => {
      const realtimeEvent = parseRealtimeEvent(event.data);

      if (!realtimeEvent) {
        return;
      }

      if (realtimeEvent.type === 'sync_required' || event.type === 'sync_required') {
        void recoverFromRest();
        return;
      }

      const nextCursor = realtimeEvent.cursor ?? realtimeEvent.sync_cursor;
      if (nextCursor) {
        cursorRef.current = nextCursor;
      }

      if (shouldRefreshForRealtimeEvent(realtimeEvent)) {
        void invalidateRealtimeQueries();
      }
    };

    const handleConnection = (event: MessageEvent<string>) => {
      const realtimeEvent = parseRealtimeEvent(event.data);
      const nextCursor = realtimeEvent?.sync_cursor ?? realtimeEvent?.cursor;

      if (nextCursor) {
        cursorRef.current = nextCursor;
      }

      setStatus('connected');
    };

    const handleOnline = () => {
      void recoverFromRest();
    };

    const handleOffline = () => {
      setStatus('offline');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    if (typeof window.EventSource !== 'function') {
      void recoverFromRest();
      return () => {
        cancelled = true;
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }

    const eventSource = new window.EventSource('/api/v1/me/realtime/sse', {
      withCredentials: true,
    });

    eventSource.addEventListener('connected', handleConnection);
    eventSource.addEventListener('message', handleRealtimeMessage);
    for (const eventName of CUSTOMER_MESSAGING_SSE_EVENTS) {
      eventSource.addEventListener(eventName, handleRealtimeMessage);
    }
    eventSource.addEventListener('error', () => {
      setStatus(navigator.onLine === false ? 'offline' : 'reconnecting');
      void recoverFromRest();
    });

    return () => {
      cancelled = true;
      for (const eventName of CUSTOMER_MESSAGING_SSE_EVENTS) {
        eventSource.removeEventListener(eventName, handleRealtimeMessage);
      }
      eventSource.close();
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [enabled, queryClient]);

  const recover = async () => {
    const { data } = await messagingApi.syncRealtime({
      cursor: cursorRef.current,
      limit: 100,
    });
    cursorRef.current = data.cursor;
    updateMessagingCachesFromSync(queryClient, data);
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.conversationLists(),
      }),
      queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.conversationDetails(),
      }),
      queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.notificationLists(),
      }),
      queryClient.invalidateQueries({
        queryKey: customerMessagingKeys.unreadCounts(),
      }),
    ]);
    setLastSyncedAt(new Date().toISOString());
    setStatus('connected');
  };

  return {
    lastSyncedAt,
    recover,
    status,
  };
}
