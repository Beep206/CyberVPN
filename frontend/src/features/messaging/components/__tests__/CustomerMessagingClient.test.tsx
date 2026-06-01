import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { server } from '@/test/mocks/server';
import { CustomerMessagingClient } from '../CustomerMessagingClient';
import { NotificationCenterDropdown } from '../NotificationCenterDropdown';

const messages = vi.hoisted(() => ({
  'Messaging.actions.refreshList': 'Refresh conversations',
  'Messaging.category.support': 'Support',
  'Messaging.description': 'Review account conversations.',
  'Messaging.detail.emptyDescription': 'Choose a thread.',
  'Messaging.detail.emptyTitle': 'Select a conversation',
  'Messaging.detail.noMessages': 'No public messages are available in this conversation.',
  'Messaging.detail.threadTitle': 'Thread',
  'Messaging.errors.detail': 'Could not load this conversation.',
  'Messaging.errors.list': 'Could not load private conversations.',
  'Messaging.eyebrow': 'Private line',
  'Messaging.filters.all': 'All conversations',
  'Messaging.filters.statusLabel': 'Filter conversations by status',
  'Messaging.list.emptyDescription': 'Admin-started conversations will appear here.',
  'Messaging.list.emptyTitle': 'No private messages',
  'Messaging.list.openConversation': 'Open conversation about {subject}',
  'Messaging.list.title': 'Conversation queue',
  'Messaging.notifications.emptyDescription': 'Account updates will appear here.',
  'Messaging.notifications.emptyTitle': 'No notifications',
  'Messaging.notifications.error': 'Could not load notifications.',
  'Messaging.notifications.eyebrow': 'Signal center',
  'Messaging.notifications.markAllRead': 'Mark all notifications read',
  'Messaging.notifications.markOneRead': 'Mark notification read',
  'Messaging.notifications.openMessages': 'Open messages',
  'Messaging.notifications.panelLabel': 'Notification center',
  'Messaging.notifications.refresh': 'Refresh notifications',
  'Messaging.notifications.severity.info': 'Info',
  'Messaging.notifications.title': 'Notifications',
  'Messaging.notifications.triggerLabel': 'Open notification center, {count} unread updates',
  'Messaging.priority.normal': 'Normal',
  'Messaging.privacy.description': 'Only public messages are shown.',
  'Messaging.privacy.title': 'Scoped customer channel',
  'Messaging.readOnly.archived.description': 'Archived threads cannot accept replies.',
  'Messaging.readOnly.archived.title': 'Conversation archived',
  'Messaging.readOnly.closed.description': 'This thread is read-only.',
  'Messaging.readOnly.closed.title': 'Conversation closed',
  'Messaging.readOnly.locked.description': 'This thread is locked.',
  'Messaging.readOnly.locked.title': 'Conversation locked',
  'Messaging.realtime.status.connected': 'Live',
  'Messaging.realtime.status.connecting': 'Connecting',
  'Messaging.realtime.status.offline': 'Offline',
  'Messaging.realtime.status.reconnecting': 'Reconnecting',
  'Messaging.realtime.status.syncing': 'Restoring',
  'Messaging.realtime.status.unavailable': 'Sync only',
  'Messaging.reply.counter': '{count}/4000 characters',
  'Messaging.reply.error': 'Could not send this reply. Try again.',
  'Messaging.reply.label': 'Reply',
  'Messaging.reply.placeholder': 'Type your reply for the support team',
  'Messaging.reply.submit': 'Send reply',
  'Messaging.reply.submitting': 'Sending...',
  'Messaging.responseState.waiting_customer': 'Waiting for you',
  'Messaging.responseState.waiting_admin': 'Waiting for support',
  'Messaging.sender.admin': 'Support',
  'Messaging.sender.customer': 'You',
  'Messaging.sender.system': 'System',
  'Messaging.status.archived': 'Archived',
  'Messaging.status.closed': 'Closed',
  'Messaging.status.locked': 'Locked',
  'Messaging.status.open': 'Open',
  'Messaging.surface': 'Customer inbox',
  'Messaging.title': 'Messages',
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: (namespace?: string) => {
    return (key: string, values?: Record<string, string | number>) => {
      const fullKey = namespace ? `${namespace}.${key}` : key;
      const template = String(messages[fullKey as keyof typeof messages] ?? fullKey);

      return template.replace(/\{(\w+)\}/g, (_match, token: string) =>
        String(values?.[token] ?? `{${token}}`),
      );
    };
  },
}));

const API_BASE = '*/api/v1';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
}

function renderWithQuery(ui: React.ReactNode) {
  const queryClient = createQueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );

  return queryClient;
}

function installMessagingHandlers({
  detailMessages = [
    {
      id: 'message-1',
      public_id: 'msg_public_1',
      conversation_id: 'conversation-1',
      sender_type: 'admin',
      visibility: 'public',
      body: 'Please reopen the app and try again.',
      created_at: '2026-05-31T10:05:00Z',
    },
    {
      id: 'message-internal',
      public_id: 'msg_internal_1',
      conversation_id: 'conversation-1',
      sender_type: 'admin',
      visibility: 'internal',
      body: 'Do not send config URLs in chat.',
      created_at: '2026-05-31T10:06:00Z',
    },
  ],
} = {}) {
  server.use(
    http.get(`${API_BASE}/me/conversations`, () =>
      HttpResponse.json({
        conversations: [
          {
            id: 'conversation-1',
            public_id: 'msg_001',
            status: 'open',
            response_state: 'waiting_customer',
            category: 'support',
            priority: 'normal',
            subject: 'Renewal access',
            unread_count: 1,
            created_at: '2026-05-31T10:00:00Z',
            updated_at: '2026-05-31T10:05:00Z',
            last_message_at: '2026-05-31T10:05:00Z',
            closed_at: null,
          },
        ],
        nextCursor: null,
      }),
    ),
    http.get(`${API_BASE}/me/conversations/msg_001`, () =>
      HttpResponse.json({
        id: 'conversation-1',
        public_id: 'msg_001',
        status: 'open',
        response_state: 'waiting_customer',
        category: 'support',
        priority: 'normal',
        subject: 'Renewal access',
        unread_count: 1,
        created_at: '2026-05-31T10:00:00Z',
        updated_at: '2026-05-31T10:05:00Z',
        last_message_at: '2026-05-31T10:05:00Z',
        closed_at: null,
        messages: detailMessages,
      }),
    ),
    http.post(`${API_BASE}/me/conversations/msg_001/read`, () =>
      HttpResponse.json({
        id: 'read-state-1',
        conversation_id: 'conversation-1',
        participant_id: 'customer-1',
        last_read_message_id: 'message-1',
        last_read_at: '2026-05-31T10:07:00Z',
        updated_at: '2026-05-31T10:07:00Z',
      }),
    ),
  );
}

describe('CustomerMessagingClient', () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.href = 'http://localhost:3000/en-EN/messages';
  });

  afterEach(() => {
    window.location.href = 'http://localhost:3000';
  });

  it('renders admin-started conversation detail and filters internal notes', async () => {
    installMessagingHandlers();

    renderWithQuery(<CustomerMessagingClient />);

    expect(await screen.findByText('Renewal access')).toBeInTheDocument();
    expect(await screen.findByText('Please reopen the app and try again.')).toBeInTheDocument();
    expect(screen.queryByText('Do not send config URLs in chat.')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /start private dialog/i })).not.toBeInTheDocument();
  });

  it('sends a customer reply into an open conversation', async () => {
    installMessagingHandlers();

    server.use(
      http.post(`${API_BASE}/me/conversations/msg_001/messages`, async ({ request }) => {
        const body = (await request.json()) as { body: string };
        expect(body.body).toBe('It works now.');
        expect(request.headers.get('Idempotency-Key')).toContain('customer-message:msg_001:');

        return HttpResponse.json({
          message: {
            id: 'message-2',
            public_id: 'msg_public_2',
            conversation_id: 'conversation-1',
            sender_type: 'customer',
            visibility: 'public',
            body: 'It works now.',
            created_at: '2026-05-31T10:08:00Z',
          },
          conversation: {
            id: 'conversation-1',
            public_id: 'msg_001',
            status: 'open',
            response_state: 'waiting_admin',
            category: 'support',
            priority: 'normal',
            subject: 'Renewal access',
            unread_count: 0,
            created_at: '2026-05-31T10:00:00Z',
            updated_at: '2026-05-31T10:08:00Z',
            last_message_at: '2026-05-31T10:08:00Z',
            closed_at: null,
          },
          created: true,
        });
      }),
    );

    const user = userEvent.setup();
    renderWithQuery(<CustomerMessagingClient />);

    const reply = await screen.findByLabelText('Reply');
    await user.type(reply, 'It works now.');
    await user.click(screen.getByRole('button', { name: 'Send reply' }));

    expect(await screen.findByText('It works now.')).toBeInTheDocument();
  });
});

class MockEventSource {
  static instances: MockEventSource[] = [];

  readonly listeners = new Map<string, Array<(event: Event) => void>>();
  readonly url: string;
  readonly withCredentials: boolean;
  close = vi.fn();

  constructor(url: string | URL, init?: EventSourceInit) {
    this.url = String(url);
    this.withCredentials = init?.withCredentials === true;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    const nextListeners = this.listeners.get(type) ?? [];
    const callback =
      typeof listener === 'function'
        ? listener
        : (event: Event) => listener.handleEvent(event);
    nextListeners.push(callback);
    this.listeners.set(type, nextListeners);
  }

  removeEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    const callbacks = this.listeners.get(type);
    if (!callbacks) {
      return;
    }

    const callback =
      typeof listener === 'function'
        ? listener
        : (event: Event) => listener.handleEvent(event);
    this.listeners.set(
      type,
      callbacks.filter((current) => current !== callback),
    );
  }

  emit(type: string, payload?: Record<string, unknown>) {
    const data = payload ? JSON.stringify(payload) : '';
    const event = new MessageEvent(type, { data });

    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

describe('NotificationCenterDropdown', () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    Object.defineProperty(window, 'EventSource', {
      configurable: true,
      value: MockEventSource,
    });
  });

  it('restores missed messages by refetching active details after custom SSE sync_required', async () => {
    let includeMissedDetailMessage = false;
    let syncRequestCursor: string | null = null;

    server.use(
      http.get(`${API_BASE}/me/conversations`, () =>
        HttpResponse.json({
          conversations: [
            {
              id: 'conversation-1',
              public_id: 'msg_001',
              status: 'open',
              response_state: 'waiting_customer',
              category: 'support',
              priority: 'normal',
              subject: 'Renewal access',
              unread_count: 1,
              created_at: '2026-05-31T10:00:00Z',
              updated_at: '2026-05-31T10:05:00Z',
              last_message_at: '2026-05-31T10:05:00Z',
              closed_at: null,
            },
          ],
          nextCursor: null,
        }),
      ),
      http.get(`${API_BASE}/me/notifications`, () =>
        HttpResponse.json({
          notifications: [
            {
              id: 'notification-1',
              delivery_id: 'delivery-1',
              notification_type: 'message',
              severity: 'info',
              title: 'Support replied',
              body: 'Open your private message.',
              action_url: null,
              aggregate_type: 'messaging_message',
              aggregate_id: 'message-1',
              conversation_id: 'conversation-1',
              message_id: 'message-1',
              status: 'delivered',
              created_at: '2026-05-31T10:05:00Z',
              updated_at: '2026-05-31T10:05:00Z',
              read_at: null,
            },
          ],
          nextCursor: null,
        }),
      ),
      http.get(`${API_BASE}/me/conversations/msg_001`, () =>
        HttpResponse.json({
          id: 'conversation-1',
          public_id: 'msg_001',
          status: 'open',
          response_state: 'waiting_customer',
          category: 'support',
          priority: 'normal',
          subject: 'Renewal access',
          unread_count: 0,
          created_at: '2026-05-31T10:00:00Z',
          updated_at: '2026-05-31T10:00:00Z',
          last_message_at: null,
          closed_at: null,
          messages: includeMissedDetailMessage
            ? [
                {
                  id: 'message-missed',
                  public_id: 'msg_public_missed',
                  conversation_id: 'conversation-1',
                  sender_type: 'admin',
                  visibility: 'public',
                  body: 'Missed admin reply',
                  created_at: '2026-05-31T10:09:00Z',
                },
              ]
            : [],
        }),
      ),
      http.get(`${API_BASE}/me/realtime/sync`, ({ request }) => {
        syncRequestCursor = new URL(request.url).searchParams.get('cursor');
        includeMissedDetailMessage = true;

        return HttpResponse.json({
          cursor: 'cursor-2',
          conversations: [
            {
              id: 'conversation-1',
              public_id: 'msg_001',
              status: 'open',
              response_state: 'waiting_customer',
              category: 'support',
              priority: 'normal',
              subject: 'Renewal access',
              unread_count: 1,
              created_at: '2026-05-31T10:00:00Z',
              updated_at: '2026-05-31T10:09:00Z',
              last_message_at: '2026-05-31T10:09:00Z',
              closed_at: null,
            },
          ],
          messages: [],
          notifications: [],
          unread_counts: {
            conversations: 1,
            notifications: 1,
          },
        });
      }),
      http.post(`${API_BASE}/me/conversations/msg_001/read`, () =>
        HttpResponse.json({
          id: 'read-state-1',
          conversation_id: 'conversation-1',
          participant_id: 'customer-1',
          last_read_message_id: 'message-missed',
          last_read_at: '2026-05-31T10:10:00Z',
          updated_at: '2026-05-31T10:10:00Z',
        }),
      ),
    );

    const queryClient = renderWithQuery(
      <>
        <NotificationCenterDropdown />
        <CustomerMessagingClient />
      </>,
    );
    const user = userEvent.setup();

    await screen.findByText('2');
    await user.click(screen.getByLabelText('Open notification center, 2 unread updates'));
    expect(await screen.findByText('Support replied')).toBeInTheDocument();

    await waitFor(() => expect(MockEventSource.instances[0]).toBeDefined());
    MockEventSource.instances[0]?.emit('connected', {
      sync_cursor: 'cursor-1',
      type: 'connected',
    });
    MockEventSource.instances[0]?.emit('sync_required', {
      type: 'sync_required',
      sync_cursor: 'cursor-newer-than-last-rest-sync',
    });

    expect(await screen.findByText('Missed admin reply')).toBeInTheDocument();
    expect(syncRequestCursor).toBe('cursor-1');
    expect(queryClient.getQueryData(['customer-messaging', 'unread-counts'])).toEqual({
      conversations: 1,
      notifications: 1,
    });
  });
});
