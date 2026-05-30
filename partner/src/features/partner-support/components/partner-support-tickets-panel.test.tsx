import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { PartnerSupportTicketsPanel } from './partner-support-tickets-panel';

const API_BASE = '*/api/v1';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
}

function renderPanel() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <PartnerSupportTicketsPanel
        access="admin"
        currentPermissionKeys={['workspace_read', 'operations_write']}
        isCanonicalWorkspace
        workspaceId="workspace_001"
        workspaceName="North Star Growth Studio"
      />
    </QueryClientProvider>,
  );
}

function ticketPayload(overrides: Record<string, unknown> = {}) {
  return {
    public_id: 'SUP-2026-001',
    status: 'open',
    category: 'setup',
    priority: 'normal',
    subject: 'Partner workspace setup',
    last_message_preview: 'Synthetic setup question.',
    created_at: '2026-05-29T10:00:00Z',
    updated_at: '2026-05-29T10:00:00Z',
    last_customer_message_at: null,
    last_support_message_at: null,
    resolved_at: null,
    closed_at: null,
    messages: [
      {
        author_label: 'partner',
        body: 'Synthetic setup question.',
        created_at: '2026-05-29T10:00:00Z',
      },
      {
        author_label: 'support',
        body: 'Public support reply.',
        created_at: '2026-05-29T10:02:00Z',
      },
    ],
    events: [
      {
        actor_label: 'partner',
        event_type: 'ticket_created',
        from_value: null,
        to_value: 'open',
        audit_summary: 'Partner ticket created.',
        created_at: '2026-05-29T10:00:00Z',
      },
      {
        event_type: 'internal_note_added',
        actor_label: 'support',
        from_value: null,
        to_value: null,
        audit_summary: 'Internal note added.',
        created_at: '2026-05-29T10:01:00Z',
      },
    ],
    ...overrides,
  };
}

describe('PartnerSupportTicketsPanel', () => {
  it('renders public DTO tickets without requiring internal ownership fields', async () => {
    let detailPath: string | null = null;

    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/support/tickets`, () =>
        HttpResponse.json({
          tickets: [ticketPayload()],
          nextCursor: null,
        }),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001`, ({ request }) => {
        detailPath = new URL(request.url).pathname;
        return HttpResponse.json(ticketPayload());
      }),
    );

    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByText('Partner workspace setup')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /SUP-2026-001/i }));

    const detailPanel = screen.getByText('detail.title').closest('section');
    expect(detailPanel).not.toBeNull();
    expect(
      await within(detailPanel as HTMLElement).findByText('Synthetic setup question.'),
    ).toBeInTheDocument();
    expect(within(detailPanel as HTMLElement).getAllByText('authors.partner').length).toBeGreaterThan(0);
    expect(within(detailPanel as HTMLElement).getByText('authors.admin')).toBeInTheDocument();
    expect(
      within(detailPanel as HTMLElement).queryByText('Internal triage note must stay hidden.'),
    ).not.toBeInTheDocument();
    expect(
      within(detailPanel as HTMLElement).queryByText('events.internal_note_added'),
    ).not.toBeInTheDocument();
    expect(
      within(detailPanel as HTMLElement).queryByText('11111111-1111-1111-1111-111111111111'),
    ).not.toBeInTheDocument();
    expect(detailPath).toBe('/api/v1/partner-workspaces/workspace_001/support/tickets/SUP-2026-001');
  });

  it('creates, replies, closes, and reopens through workspace-scoped calls', async () => {
    let ticketStatus = 'open';
    const captured: {
      createBody?: Record<string, unknown>;
      replyBody?: Record<string, unknown>;
      closePath?: string;
      reopenPath?: string;
    } = {};

    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/support/tickets`, () =>
        HttpResponse.json({
          tickets: [ticketPayload({ status: ticketStatus })],
          nextCursor: null,
        }),
      ),
      http.get(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001`, () =>
        HttpResponse.json(ticketPayload({ status: ticketStatus })),
      ),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets`, async ({ request }) => {
        captured.createBody = await request.json() as Record<string, unknown>;
        return HttpResponse.json(
          ticketPayload({
            public_id: 'SUP-2026-002',
            subject: captured.createBody.subject,
            last_message_preview: captured.createBody.message,
          }),
          { status: 201 },
        );
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/replies`, async ({ request }) => {
        captured.replyBody = await request.json() as Record<string, unknown>;
        ticketStatus = 'pending_support';
        return HttpResponse.json(ticketPayload({ status: ticketStatus }));
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/close`, ({ request }) => {
        captured.closePath = new URL(request.url).pathname;
        ticketStatus = 'closed';
        return HttpResponse.json(ticketPayload({ status: ticketStatus }));
      }),
      http.post(`${API_BASE}/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/reopen`, ({ request }) => {
        captured.reopenPath = new URL(request.url).pathname;
        ticketStatus = 'pending_support';
        return HttpResponse.json(ticketPayload({ status: ticketStatus }));
      }),
    );

    const user = userEvent.setup();
    renderPanel();

    await user.type(screen.getByLabelText('create.subjectLabel'), 'New partner issue');
    await user.selectOptions(screen.getByLabelText('create.categoryLabel'), 'setup');
    await user.type(screen.getByLabelText('create.messageLabel'), 'Synthetic only support request.');
    await user.click(screen.getByRole('button', { name: 'create.submit' }));

    await waitFor(() => {
      expect(captured.createBody).toMatchObject({
        category: 'setup',
        message: 'Synthetic only support request.',
        priority: 'normal',
        subject: 'New partner issue',
      });
    });
    expect(captured.createBody).not.toHaveProperty('metadata');
    expect(captured.createBody).not.toHaveProperty('source');
    expect(await screen.findByText('create.success')).toBeInTheDocument();

    await user.click(await screen.findByRole('button', { name: /SUP-2026-001/i }));

    const detailPanel = screen.getByText('detail.title').closest('section');
    expect(detailPanel).not.toBeNull();

    await user.type(
      within(detailPanel as HTMLElement).getByLabelText('detail.replyLabel'),
      'Partner reply for support.',
    );
    await user.click(within(detailPanel as HTMLElement).getByRole('button', { name: 'detail.replyAction' }));

    await waitFor(() => {
      expect(captured.replyBody).toEqual({ message: 'Partner reply for support.' });
    });
    expect(await screen.findByText('detail.replySuccess')).toBeInTheDocument();

    await user.click(within(detailPanel as HTMLElement).getByRole('button', { name: 'detail.closeAction' }));

    await waitFor(() => {
      expect(captured.closePath).toBe('/api/v1/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/close');
    });
    expect(await screen.findByText('detail.closeSuccess')).toBeInTheDocument();

    await user.click(await within(detailPanel as HTMLElement).findByRole('button', { name: 'detail.reopenAction' }));

    await waitFor(() => {
      expect(captured.reopenPath).toBe('/api/v1/partner-workspaces/workspace_001/support/tickets/SUP-2026-001/reopen');
    });
    expect(await screen.findByText('detail.reopenSuccess')).toBeInTheDocument();
  });
});
