import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SupportConsole } from '../support-console';
import type { SupportTicketDetail, SupportTicketSummary } from '@/lib/api/support';

const {
  mockAddAdminInternalNote,
  mockAddAdminReply,
  mockGetAdminTicket,
  mockListAdminTickets,
  mockRouterReplace,
  mockSession,
  mockUpdateAdminTicket,
} = vi.hoisted(() => ({
  mockAddAdminInternalNote: vi.fn(),
  mockAddAdminReply: vi.fn(),
  mockGetAdminTicket: vi.fn(),
  mockListAdminTickets: vi.fn(),
  mockRouterReplace: vi.fn(),
  mockSession: vi.fn(),
  mockUpdateAdminTicket: vi.fn(),
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...props
  }: Record<string, unknown> & { href?: string }) => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { createElement } = require('react');
    return createElement('a', { href, ...props }, children);
  },
  useRouter: () => ({
    back: vi.fn(),
    prefetch: vi.fn(),
    push: vi.fn(),
    replace: mockRouterReplace,
  }),
}));

vi.mock('@/lib/api/auth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/auth')>('@/lib/api/auth');
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      session: (...args: unknown[]) => mockSession(...args),
    },
  };
});

vi.mock('@/lib/api/support', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/support')>('@/lib/api/support');
  return {
    ...actual,
    supportApi: {
      addAdminInternalNote: (...args: unknown[]) => mockAddAdminInternalNote(...args),
      addAdminReply: (...args: unknown[]) => mockAddAdminReply(...args),
      getAdminTicket: (...args: unknown[]) => mockGetAdminTicket(...args),
      listAdminTickets: (...args: unknown[]) => mockListAdminTickets(...args),
      updateAdminTicket: (...args: unknown[]) => mockUpdateAdminTicket(...args),
    },
  };
});

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

function buildTicket(overrides: Partial<SupportTicketDetail> = {}): SupportTicketDetail {
  return {
    assigned_admin_id: null,
    category: 'setup',
    closed_at: null,
    created_at: '2026-05-29T10:00:00Z',
    customer_account_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
    events: [
      {
        actor_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
        actor_type: 'admin',
        audit_summary: 'Internal note added',
        created_at: '2026-05-29T10:30:00Z',
        event_type: 'internal_note_added',
        from_value: null,
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0301',
        ticket_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        to_value: null,
      },
    ],
    id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
    last_customer_message_at: '2026-05-29T10:00:00Z',
    last_message_preview: 'Setup is failing.',
    last_support_message_at: '2026-05-29T10:20:00Z',
    messages: [
      {
        author_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
        author_type: 'customer',
        body: 'Setup is failing.',
        created_at: '2026-05-29T10:00:00Z',
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0201',
        ticket_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        visibility: 'public',
      },
      {
        author_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
        author_type: 'admin',
        body: 'Operator-only diagnostic note.',
        created_at: '2026-05-29T10:30:00Z',
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0202',
        ticket_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        visibility: 'internal',
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
    updated_at: '2026-05-29T10:30:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockRouterReplace.mockClear();
  const ticket = buildTicket();
  mockSession.mockResolvedValue({
    data: {
      created_at: '2026-05-01T00:00:00Z',
      email: 'support@example.com',
      id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
      is_active: true,
      is_email_verified: true,
      login: 'support',
      role: 'support',
      telegram_id: null,
    },
  });
  mockListAdminTickets.mockResolvedValue({
    data: {
      tickets: [ticket satisfies SupportTicketSummary],
      nextCursor: null,
    },
  });
  mockGetAdminTicket.mockResolvedValue({ data: ticket });
  mockAddAdminReply.mockResolvedValue({ data: ticket });
  mockAddAdminInternalNote.mockResolvedValue({ data: ticket });
  mockUpdateAdminTicket.mockResolvedValue({ data: ticket });
});

describe('SupportConsole', () => {
  it('renders public messages, internal messages, and separate composers', async () => {
    renderWithQueryClient(<SupportConsole />);

    expect((await screen.findAllByText('sup_20260529_0001')).length).toBeGreaterThan(0);
    expect(await screen.findByTestId('support-public-reply-composer')).toBeInTheDocument();
    expect(screen.getByTestId('support-internal-note-composer')).toBeInTheDocument();
    expect(screen.getByTestId('support-public-message')).toHaveTextContent('Setup is failing.');
    expect(screen.getByTestId('support-internal-message')).toHaveTextContent(
      'Operator-only diagnostic note.',
    );
  });

  it('posts public replies and internal notes to different API methods', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<SupportConsole initialTicketRef="sup_20260529_0001" />);

    const publicComposer = await screen.findByTestId('support-public-reply-composer');
    await user.type(
      within(publicComposer).getByLabelText('reply.message'),
      'Public troubleshooting steps.',
    );
    fireEvent.submit(publicComposer);

    await waitFor(() => {
      expect(mockAddAdminReply).toHaveBeenCalledWith('sup_20260529_0001', {
        message: 'Public troubleshooting steps.',
      });
    });
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('feedback.publicReplySent');
    });
    expect(mockAddAdminInternalNote).not.toHaveBeenCalled();

    const internalComposer = screen.getByTestId('support-internal-note-composer');
    await user.type(
      within(internalComposer).getByLabelText('internalNote.message'),
      'Internal operator note.',
    );
    fireEvent.submit(internalComposer);

    await waitFor(() => {
      expect(mockAddAdminInternalNote).toHaveBeenCalledWith('sup_20260529_0001', {
        message: 'Internal operator note.',
      });
    });
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('feedback.internalNoteSaved');
    });
  });

  it('hydrates support filters from URL state and preserves them in route updates', async () => {
    renderWithQueryClient(
      <SupportConsole
        initialSearchParams={{
          assignment: 'mine',
          category: 'setup',
          priority: 'high',
          q: 'setup',
          source: 'customer_web',
          status: 'pending_support',
        }}
      />,
    );

    expect(await screen.findByLabelText('filters.search')).toHaveValue('setup');

    await waitFor(() => {
      expect(mockListAdminTickets).toHaveBeenCalledWith(expect.objectContaining({
        assigned_admin_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
        category: 'setup',
        limit: 50,
        priority: 'high',
        query: 'setup',
        source: 'customer_web',
        status: 'pending_support',
      }));
    });
    await waitFor(() => {
      expect(mockRouterReplace).toHaveBeenCalledWith(
        expect.stringContaining('assignment=mine'),
        { scroll: false },
      );
    });
  });

  it('renders compact mobile tickets and visible focus classes for triage controls', async () => {
    renderWithQueryClient(<SupportConsole />);

    const mobileList = await screen.findByTestId('support-mobile-ticket-list');
    expect(mobileList).toHaveTextContent('Windows setup failed');
    expect(within(mobileList).getByRole('button', { name: 'list.selectTicket' }))
      .toHaveClass('focus-visible:ring-2');
    expect(within(mobileList).getByRole('link', { name: 'list.openRoute' }))
      .toHaveClass('focus-visible:ring-2');
    expect(screen.getByLabelText('filters.search')).toHaveClass('focus-visible:ring-2');
    expect(screen.getByRole('button', { name: 'filters.assignment.mine' }))
      .toHaveClass('focus-visible:ring-2');
  });

  it('announces metadata updates and documents client-scoped unassigned filtering', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<SupportConsole />);

    const saveButton = await screen.findByRole('button', { name: 'actions.save' });
    expect(saveButton).toHaveClass('focus-visible:ring-2');
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateAdminTicket).toHaveBeenCalledWith('sup_20260529_0001', {
        assigned_admin_id: null,
        category: 'setup',
        priority: 'high',
        status: 'pending_support',
      });
    });
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('feedback.ticketUpdated');
    });

    const resolvedButton = screen.getByRole('button', { name: 'actions.quick.resolved' });
    expect(resolvedButton).toHaveClass('focus-visible:ring-2');
    await user.click(resolvedButton);

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('feedback.statusUpdated');
    });

    await user.click(screen.getByRole('button', { name: 'filters.assignment.unassigned' }));
    expect(await screen.findByText('filters.assignment.unassignedScopeHint')).toBeInTheDocument();
    await waitFor(() => {
      expect(mockRouterReplace).toHaveBeenCalledWith(
        expect.stringContaining('assignment=unassigned'),
        { scroll: false },
      );
    });
  });

  it('shows a permission-denied state and avoids support reads for roles without support_ticket_read', async () => {
    for (const role of ['viewer', 'finance', 'operator', 'user']) {
      vi.clearAllMocks();
      mockRouterReplace.mockClear();
      mockSession.mockResolvedValueOnce({
        data: {
          created_at: '2026-05-01T00:00:00Z',
          email: `${role}@example.com`,
          id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
          is_active: true,
          is_email_verified: true,
          login: role,
          role,
          telegram_id: null,
        },
      });

      const { unmount } = renderWithQueryClient(<SupportConsole />);

      expect(await screen.findByText('permissionDenied.title')).toBeInTheDocument();
      expect(mockListAdminTickets).not.toHaveBeenCalled();
      expect(mockGetAdminTicket).not.toHaveBeenCalled();

      unmount();
    }
  });
});
