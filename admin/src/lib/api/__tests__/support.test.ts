import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import {
  supportApi,
  type SupportTicketDetail,
  type SupportTicketSummary,
} from '../support';

const API_MATCH = {
  adminTickets: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/support\/tickets(?:\?.*)?$/,
  adminTicketByRef: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/support\/tickets\/[^/]+$/,
  adminTicketReplies: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/support\/tickets\/[^/]+\/replies$/,
  adminTicketInternalNotes: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/support\/tickets\/[^/]+\/internal-notes$/,
};

function buildSupportTicket(overrides: Partial<SupportTicketDetail> = {}): SupportTicketDetail {
  return {
    assigned_admin_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
    category: 'setup',
    closed_at: null,
    created_at: '2026-05-29T10:00:00Z',
    customer_account_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
    events: [
      {
        actor_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
        actor_type: 'admin',
        audit_summary: 'Admin public reply added',
        created_at: '2026-05-29T10:20:00Z',
        event_type: 'public_reply_added',
        from_value: null,
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0101',
        ticket_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        to_value: null,
      },
    ],
    id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
    last_customer_message_at: '2026-05-29T10:00:00Z',
    last_message_preview: 'Cannot finish setup.',
    last_support_message_at: '2026-05-29T10:20:00Z',
    messages: [
      {
        author_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
        author_type: 'customer',
        body: 'Cannot finish setup.',
        created_at: '2026-05-29T10:00:00Z',
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0201',
        ticket_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        visibility: 'public',
      },
    ],
    owner_type: 'customer',
    partner_workspace_id: null,
    priority: 'high',
    public_id: 'sup_20260529_0001',
    resolved_at: null,
    source: 'customer_web',
    status: 'pending_support',
    subject: 'Windows setup failed',
    updated_at: '2026-05-29T10:20:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  globalThis.localStorage?.clear();
  if (typeof window !== 'undefined') {
    window.location.href = 'http://localhost:3000';
  }
});

afterEach(() => {
  if (typeof window !== 'undefined') {
    window.location.href = 'http://localhost:3000';
  }
});

describe('supportApi admin support operations', () => {
  it('lists admin support tickets with filters', async () => {
    let capturedUrl: URL | null = null;
    const ticket = buildSupportTicket();

    server.use(
      http.get(API_MATCH.adminTickets, ({ request }) => {
        capturedUrl = new URL(request.url);
        return HttpResponse.json({
          tickets: [ticket satisfies SupportTicketSummary],
          nextCursor: 'cursor_2',
        });
      }),
    );

    const response = await supportApi.listAdminTickets({
      category: 'setup',
      limit: 25,
      priority: 'high',
      query: 'sup_20260529_0001',
      source: 'customer_web',
      status: 'pending_support',
    });

    expect(response.status).toBe(200);
    expect(response.data.tickets[0]?.public_id).toBe('sup_20260529_0001');
    expect(capturedUrl?.searchParams.get('status')).toBe('pending_support');
    expect(capturedUrl?.searchParams.get('priority')).toBe('high');
    expect(capturedUrl?.searchParams.get('category')).toBe('setup');
    expect(capturedUrl?.searchParams.get('source')).toBe('customer_web');
    expect(capturedUrl?.searchParams.get('query')).toBe('sup_20260529_0001');
    expect(capturedUrl?.searchParams.get('limit')).toBe('25');
  });

  it('keeps public replies and internal notes on separate endpoints', async () => {
    const capturedBodies: Record<string, unknown>[] = [];
    const ticket = buildSupportTicket();

    server.use(
      http.post(API_MATCH.adminTicketReplies, async ({ request }) => {
        capturedBodies.push({
          endpoint: 'replies',
          body: await request.json(),
        });
        return HttpResponse.json(ticket);
      }),
      http.post(API_MATCH.adminTicketInternalNotes, async ({ request }) => {
        capturedBodies.push({
          endpoint: 'internal-notes',
          body: await request.json(),
        });
        return HttpResponse.json(ticket);
      }),
    );

    await supportApi.addAdminReply('sup_20260529_0001', {
      message: 'Public answer.',
    });
    await supportApi.addAdminInternalNote('sup_20260529_0001', {
      message: 'Internal operator note.',
    });

    expect(capturedBodies).toEqual([
      {
        endpoint: 'replies',
        body: { message: 'Public answer.' },
      },
      {
        endpoint: 'internal-notes',
        body: { message: 'Internal operator note.' },
      },
    ]);
  });

  it('updates admin ticket metadata with nullable assignment', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.patch(API_MATCH.adminTicketByRef, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(buildSupportTicket({
          assigned_admin_id: null,
          priority: 'urgent',
          status: 'resolved',
        }));
      }),
    );

    const response = await supportApi.updateAdminTicket('sup_20260529_0001', {
      assigned_admin_id: null,
      category: 'billing',
      priority: 'urgent',
      status: 'resolved',
    });

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('resolved');
    expect(capturedBody).toEqual({
      assigned_admin_id: null,
      category: 'billing',
      priority: 'urgent',
      status: 'resolved',
    });
  });
});
