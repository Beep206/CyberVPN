import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { supportTicketsApi } from '../support-tickets';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('supportTicketsApi', () => {
  it('lists current customer support tickets with filters', async () => {
    let capturedUrl: URL | null = null;
    server.use(
      http.get(`${API_BASE}/support/tickets`, ({ request }) => {
        capturedUrl = new URL(request.url);
        return HttpResponse.json({
          tickets: [
            {
              public_id: 'SUP-20260529-001',
              status: 'pending_support',
              category: 'vpn_access',
              priority: 'normal',
              subject: 'VPN access is not ready',
              last_message_preview: 'Provisioning still looks pending.',
              created_at: '2026-05-29T13:10:00Z',
              updated_at: '2026-05-29T13:11:00Z',
              last_customer_message_at: '2026-05-29T13:10:00Z',
              last_support_message_at: null,
              resolved_at: null,
              closed_at: null,
            },
          ],
          nextCursor: null,
        });
      }),
    );

    const response = await supportTicketsApi.list({
      category: 'vpn_access',
      limit: 25,
      status: 'pending_support',
    });

    expect(response.status).toBe(200);
    expect(capturedUrl?.searchParams.get('category')).toBe('vpn_access');
    expect(capturedUrl?.searchParams.get('limit')).toBe('25');
    expect(capturedUrl?.searchParams.get('status')).toBe('pending_support');
    expect(response.data.tickets[0]?.public_id).toBe('SUP-20260529-001');
  });

  it('creates a customer support ticket without leaking a surface source field', async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/support/tickets`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            public_id: 'SUP-20260529-002',
            status: 'pending_support',
            category: 'billing',
            priority: 'normal',
            subject: 'Payment confirmed but access missing',
            last_message_preview: 'Payment is final but VPN is not ready.',
            created_at: '2026-05-29T13:12:00Z',
            updated_at: '2026-05-29T13:12:00Z',
            last_customer_message_at: '2026-05-29T13:12:00Z',
            last_support_message_at: null,
            resolved_at: null,
            closed_at: null,
            messages: [
              {
                author_label: 'customer',
                body: 'Payment is final but VPN is not ready.',
                created_at: '2026-05-29T13:12:00Z',
              },
            ],
            events: [],
          },
          { status: 201 },
        );
      }),
    );

    const response = await supportTicketsApi.create({
      category: 'billing',
      message: 'Payment is final but VPN is not ready.',
      priority: 'normal',
      subject: 'Payment confirmed but access missing',
    });

    expect(response.status).toBe(201);
    expect(capturedBody).toEqual({
      category: 'billing',
      message: 'Payment is final but VPN is not ready.',
      priority: 'normal',
      subject: 'Payment confirmed but access missing',
    });
    expect(capturedBody).not.toHaveProperty('source');
    expect(response.data.messages[0]?.author_label).toBe('customer');
  });

  it('loads detail, replies, closes, and reopens by public ticket id', async () => {
    const requestedPaths: string[] = [];
    server.use(
      http.get(`${API_BASE}/support/tickets/SUP-20260529-003`, ({ request }) => {
        requestedPaths.push(new URL(request.url).pathname);
        return HttpResponse.json({
          public_id: 'SUP-20260529-003',
          status: 'open',
          category: 'setup',
          priority: 'normal',
          subject: 'Setup question',
          last_message_preview: 'How do I import the profile?',
          created_at: '2026-05-29T13:13:00Z',
          updated_at: '2026-05-29T13:13:00Z',
          last_customer_message_at: '2026-05-29T13:13:00Z',
          last_support_message_at: null,
          resolved_at: null,
          closed_at: null,
          messages: [],
          events: [],
        });
      }),
      http.post(`${API_BASE}/support/tickets/SUP-20260529-003/replies`, async ({ request }) => {
        requestedPaths.push(new URL(request.url).pathname);
        const body = (await request.json()) as { message: string };
        expect(body.message).toBe('Safe follow-up');
        return HttpResponse.json({
          public_id: 'SUP-20260529-003',
          status: 'pending_support',
          category: 'setup',
          priority: 'normal',
          subject: 'Setup question',
          last_message_preview: 'Safe follow-up',
          created_at: '2026-05-29T13:13:00Z',
          updated_at: '2026-05-29T13:14:00Z',
          last_customer_message_at: '2026-05-29T13:14:00Z',
          last_support_message_at: null,
          resolved_at: null,
          closed_at: null,
          messages: [],
          events: [],
        });
      }),
      http.post(`${API_BASE}/support/tickets/SUP-20260529-003/close`, ({ request }) => {
        requestedPaths.push(new URL(request.url).pathname);
        return HttpResponse.json({
          public_id: 'SUP-20260529-003',
          status: 'closed',
          category: 'setup',
          priority: 'normal',
          subject: 'Setup question',
          last_message_preview: 'Safe follow-up',
          created_at: '2026-05-29T13:13:00Z',
          updated_at: '2026-05-29T13:15:00Z',
          last_customer_message_at: '2026-05-29T13:14:00Z',
          last_support_message_at: null,
          resolved_at: null,
          closed_at: '2026-05-29T13:15:00Z',
          messages: [],
          events: [],
        });
      }),
      http.post(`${API_BASE}/support/tickets/SUP-20260529-003/reopen`, ({ request }) => {
        requestedPaths.push(new URL(request.url).pathname);
        return HttpResponse.json({
          public_id: 'SUP-20260529-003',
          status: 'pending_support',
          category: 'setup',
          priority: 'normal',
          subject: 'Setup question',
          last_message_preview: 'Safe follow-up',
          created_at: '2026-05-29T13:13:00Z',
          updated_at: '2026-05-29T13:16:00Z',
          last_customer_message_at: '2026-05-29T13:14:00Z',
          last_support_message_at: null,
          resolved_at: null,
          closed_at: null,
          messages: [],
          events: [],
        });
      }),
    );

    await supportTicketsApi.get('SUP-20260529-003');
    await supportTicketsApi.reply('SUP-20260529-003', { message: 'Safe follow-up' });
    await supportTicketsApi.close('SUP-20260529-003');
    await supportTicketsApi.reopen('SUP-20260529-003');

    expect(requestedPaths).toEqual([
      '/api/v1/support/tickets/SUP-20260529-003',
      '/api/v1/support/tickets/SUP-20260529-003/replies',
      '/api/v1/support/tickets/SUP-20260529-003/close',
      '/api/v1/support/tickets/SUP-20260529-003/reopen',
    ]);
  });
});
