import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { messagingApi } from '../messaging';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('messagingApi', () => {
  it('lists customer-owned private conversations', async () => {
    server.use(
      http.get(`${API_BASE}/me/conversations`, ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get('status')).toBe('open');

        return HttpResponse.json({
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
        });
      }),
    );

    const response = await messagingApi.listConversations({ status: 'open' });

    expect(response.status).toBe(200);
    expect(response.data.conversations[0]?.public_id).toBe('msg_001');
    expect(response.data.conversations[0]?.unread_count).toBe(1);
  });

  it('loads conversation detail with public customer response shape', async () => {
    server.use(
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
          messages: [
            {
              id: 'message-1',
              public_id: 'msg_public_1',
              conversation_id: 'conversation-1',
              sender_type: 'admin',
              visibility: 'public',
              body: 'Please reopen the app and try again.',
              created_at: '2026-05-31T10:05:00Z',
            },
          ],
        }),
      ),
    );

    const response = await messagingApi.getConversation('msg_001');

    expect(response.status).toBe(200);
    expect(response.data.messages[0]?.visibility).toBe('public');
    expect(response.data.messages[0]?.body).toContain('reopen the app');
  });

  it('replies with body-level client id and idempotency header', async () => {
    server.use(
      http.post(`${API_BASE}/me/conversations/msg_001/messages`, async ({ request }) => {
        const body = (await request.json()) as {
          body: string;
          client_message_id?: string;
        };

        expect(request.headers.get('Idempotency-Key')).toBe('idem-1');
        expect(body).toEqual({
          body: 'It works now.',
          client_message_id: 'web_message_1',
        });

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

    const response = await messagingApi.replyToConversation(
      'msg_001',
      {
        body: 'It works now.',
        client_message_id: 'web_message_1',
      },
      'idem-1',
    );

    expect(response.status).toBe(200);
    expect(response.data.created).toBe(true);
    expect(response.data.message.sender_type).toBe('customer');
  });

  it('does not expose a customer private conversation creation helper', () => {
    expect('createConversation' in messagingApi).toBe(false);
  });

  it('marks notifications read and restores missed state through REST sync', async () => {
    server.use(
      http.post(`${API_BASE}/me/notifications/read`, async ({ request }) => {
        const body = (await request.json()) as { notification_ids: string[] };
        expect(body.notification_ids).toEqual(['notification-1']);

        return HttpResponse.json({
          notifications: [
            {
              id: 'notification-1',
              delivery_id: 'delivery-1',
              notification_type: 'message',
              severity: 'info',
              title: 'Support replied',
              body: 'Open your private message.',
              action_url: '/messages?conversation=conversation-1',
              aggregate_type: 'messaging_message',
              aggregate_id: 'message-1',
              conversation_id: 'conversation-1',
              message_id: 'message-1',
              status: 'read',
              created_at: '2026-05-31T10:05:00Z',
              updated_at: '2026-05-31T10:06:00Z',
              read_at: '2026-05-31T10:06:00Z',
            },
          ],
        });
      }),
      http.get(`${API_BASE}/me/realtime/sync`, ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get('cursor')).toBe('cursor-1');

        return HttpResponse.json({
          cursor: 'cursor-2',
          conversations: [],
          messages: [],
          notifications: [],
          unread_counts: {
            conversations: 0,
            notifications: 0,
          },
        });
      }),
    );

    const readResponse = await messagingApi.markNotificationsRead({
      notification_ids: ['notification-1'],
    });
    const syncResponse = await messagingApi.syncRealtime({ cursor: 'cursor-1' });

    expect(readResponse.data.notifications[0]?.status).toBe('read');
    expect(syncResponse.data.cursor).toBe('cursor-2');
    expect(syncResponse.data.unread_counts).toEqual({
      conversations: 0,
      notifications: 0,
    });
  });

  it('dismisses customer notifications through the scoped customer endpoint', async () => {
    server.use(
      http.post(`${API_BASE}/me/notifications/dismiss`, async ({ request }) => {
        const body = (await request.json()) as { notification_ids: string[] };
        expect(body.notification_ids).toEqual(['notification-1']);

        return HttpResponse.json({
          notifications: [
            {
              id: 'notification-1',
              delivery_id: 'delivery-1',
              notification_type: 'system',
              severity: 'warning',
              title: 'Maintenance window',
              body: 'Planned maintenance starts soon.',
              action_url: null,
              aggregate_type: 'system_notice',
              aggregate_id: 'notice-1',
              conversation_id: null,
              message_id: null,
              status: 'dismissed',
              created_at: '2026-05-31T10:05:00Z',
              updated_at: '2026-05-31T10:06:00Z',
              read_at: null,
            },
          ],
        });
      }),
    );

    const response = await messagingApi.dismissNotifications({
      notification_ids: ['notification-1'],
    });

    expect(response.status).toBe(200);
    expect(response.data.notifications[0]?.status).toBe('dismissed');
  });
});
