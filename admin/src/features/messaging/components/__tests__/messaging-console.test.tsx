import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MessagingConsole } from '../messaging-console';
import type {
  AdminMessagingConversationDetail,
  AdminMessagingConversationSummary,
} from '@/lib/api/messaging';

const {
  mockAddAdminInternalNote,
  mockAddAdminMessage,
  mockCloseAdminConversation,
  mockCreateAdminConversation,
  mockGetAdminConversation,
  mockListAdminConversations,
  mockReopenAdminConversation,
  mockRouterReplace,
  mockSession,
  mockUpdateAdminConversation,
} = vi.hoisted(() => ({
  mockAddAdminInternalNote: vi.fn(),
  mockAddAdminMessage: vi.fn(),
  mockCloseAdminConversation: vi.fn(),
  mockCreateAdminConversation: vi.fn(),
  mockGetAdminConversation: vi.fn(),
  mockListAdminConversations: vi.fn(),
  mockReopenAdminConversation: vi.fn(),
  mockRouterReplace: vi.fn(),
  mockSession: vi.fn(),
  mockUpdateAdminConversation: vi.fn(),
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

vi.mock('@/lib/api/messaging', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/messaging')>(
    '@/lib/api/messaging',
  );
  return {
    ...actual,
    messagingApi: {
      addAdminInternalNote: (...args: unknown[]) => mockAddAdminInternalNote(...args),
      addAdminMessage: (...args: unknown[]) => mockAddAdminMessage(...args),
      closeAdminConversation: (...args: unknown[]) => mockCloseAdminConversation(...args),
      createAdminConversation: (...args: unknown[]) => mockCreateAdminConversation(...args),
      getAdminConversation: (...args: unknown[]) => mockGetAdminConversation(...args),
      listAdminConversations: (...args: unknown[]) => mockListAdminConversations(...args),
      reopenAdminConversation: (...args: unknown[]) => mockReopenAdminConversation(...args),
      updateAdminConversation: (...args: unknown[]) => mockUpdateAdminConversation(...args),
    },
  };
});

class MockEventSource {
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;

  addEventListener = vi.fn();
  close = vi.fn();
}

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

function buildConversation(
  overrides: Partial<AdminMessagingConversationDetail> = {},
): AdminMessagingConversationDetail {
  return {
    assigned_admin_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
    category: 'support',
    closed_at: null,
    created_at: '2026-05-31T10:00:00Z',
    created_by_admin_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
    customer_account_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
    id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
    last_message_at: '2026-05-31T10:30:00Z',
    messages: [
      {
        body: 'Customer reply body.',
        body_format: 'plain_text',
        client_message_id: 'cust-msg-1',
        conversation_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        created_at: '2026-05-31T10:10:00Z',
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0201',
        public_id: 'msg_20260531_0001',
        sender_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
        sender_type: 'customer',
        updated_at: '2026-05-31T10:10:00Z',
        visibility: 'public',
      },
      {
        body: 'Admin-only diagnostic note.',
        body_format: 'plain_text',
        client_message_id: 'admin-note-1',
        conversation_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        created_at: '2026-05-31T10:30:00Z',
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0202',
        public_id: 'msg_20260531_0002',
        sender_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
        sender_type: 'admin',
        updated_at: '2026-05-31T10:30:00Z',
        visibility: 'internal',
      },
    ],
    priority: 'high',
    public_id: 'msg_20260531_0001',
    read_states: [
      {
        conversation_id: '8ef69814-83a8-4591-b3d4-9f749cbd0000',
        id: '8ef69814-83a8-4591-b3d4-9f749cbd0301',
        last_read_at: '2026-05-31T10:12:00Z',
        last_read_message_id: '8ef69814-83a8-4591-b3d4-9f749cbd0201',
        participant_id: '2fc0360d-3f88-4619-b813-d3f20e2c1234',
        updated_at: '2026-05-31T10:12:00Z',
      },
    ],
    related_support_ticket_id: null,
    response_state: 'waiting_admin',
    status: 'open',
    subject: 'Private setup follow-up',
    updated_at: '2026-05-31T10:30:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(globalThis, 'EventSource', {
    configurable: true,
    value: MockEventSource,
  });
  const conversation = buildConversation();
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
  mockListAdminConversations.mockResolvedValue({
    data: {
      conversations: [conversation satisfies AdminMessagingConversationSummary],
      nextCursor: null,
    },
  });
  mockGetAdminConversation.mockResolvedValue({ data: conversation });
  mockCreateAdminConversation.mockResolvedValue({ data: conversation });
  mockAddAdminMessage.mockResolvedValue({
    data: {
      conversation,
      created: true,
      message: conversation.messages[0],
    },
  });
  mockAddAdminInternalNote.mockResolvedValue({
    data: {
      conversation,
      created: true,
      message: conversation.messages[1],
    },
  });
  mockUpdateAdminConversation.mockResolvedValue({ data: conversation });
  mockCloseAdminConversation.mockResolvedValue({
    data: buildConversation({ closed_at: '2026-05-31T11:00:00Z', status: 'closed' }),
  });
  mockReopenAdminConversation.mockResolvedValue({ data: conversation });
});

describe('MessagingConsole', () => {
  it('renders public messages, internal notes, unread state, and read states', async () => {
    renderWithQueryClient(<MessagingConsole />);

    expect((await screen.findAllByText('msg_20260531_0001')).length).toBeGreaterThan(0);
    expect(await screen.findByTestId('messaging-public-message')).toHaveTextContent('Customer reply body.');
    expect(await screen.findByTestId('messaging-internal-message')).toHaveTextContent(
      'Admin-only diagnostic note.',
    );
    expect(screen.getAllByText('states.unread').length).toBeGreaterThan(0);
    expect(screen.getAllByText('statuses.open').length).toBeGreaterThan(0);
    expect(screen.getAllByText('priorities.high').length).toBeGreaterThan(0);
    expect(screen.getAllByText('responseStates.waiting_admin').length).toBeGreaterThan(0);
    expect(screen.getByText('senders.customer')).toBeInTheDocument();
    expect(screen.getByText('visibilities.public')).toBeInTheDocument();
    expect(screen.getByText('readStates.title')).toBeInTheDocument();
  });

  it('shows inline create validation errors and focuses the first invalid field', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<MessagingConsole />);

    const createForm = await screen.findByTestId('messaging-create-conversation-form');
    const customerInput = within(createForm).getByLabelText('create.customer');
    const subjectInput = within(createForm).getByLabelText('create.subject');
    const messageInput = within(createForm).getByLabelText('create.initialMessage');

    fireEvent.submit(createForm);

    expect(mockCreateAdminConversation).not.toHaveBeenCalled();
    expect(await within(createForm).findByText('feedback.customerRequired')).toBeInTheDocument();
    expect(customerInput).toHaveFocus();

    await user.type(customerInput, '8ef69814-83a8-4591-b3d4-9f749cbd0001');
    fireEvent.change(subjectInput, { target: { value: 'x'.repeat(161) } });
    await user.type(messageInput, 'We can continue this setup privately.');
    fireEvent.submit(createForm);

    expect(mockCreateAdminConversation).not.toHaveBeenCalled();
    expect(await within(createForm).findByText('feedback.subjectTooLong')).toBeInTheDocument();
    expect(subjectInput).toHaveFocus();
  });

  it('creates an admin-initiated conversation with a prefilled customer profile entry point', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <MessagingConsole
        initialSearchParams={{ customer: '8ef69814-83a8-4591-b3d4-9f749cbd0001' }}
      />,
    );

    const createForm = await screen.findByTestId('messaging-create-conversation-form');
    expect(within(createForm).getByLabelText('create.customer')).toHaveValue(
      '8ef69814-83a8-4591-b3d4-9f749cbd0001',
    );

    await user.type(within(createForm).getByLabelText('create.subject'), 'Private setup follow-up');
    await user.type(
      within(createForm).getByLabelText('create.initialMessage'),
      'We can continue this setup privately.',
    );
    fireEvent.submit(createForm);

    await waitFor(() => {
      expect(mockCreateAdminConversation).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_account_id: '8ef69814-83a8-4591-b3d4-9f749cbd0001',
          initial_message: expect.objectContaining({
            body: 'We can continue this setup privately.',
            client_message_id: expect.any(String),
          }),
          subject: 'Private setup follow-up',
        }),
        expect.any(String),
      );
    });
  });

  it('loads the next cursor page and shows an end-of-queue state', async () => {
    const conversation = buildConversation();
    const nextConversation = buildConversation({
      id: '8ef69814-83a8-4591-b3d4-9f749cbd0042',
      public_id: 'msg_20260531_0042',
      subject: 'Second private thread',
      updated_at: '2026-05-31T11:00:00Z',
    });
    mockListAdminConversations
      .mockResolvedValueOnce({
        data: {
          conversations: [conversation satisfies AdminMessagingConversationSummary],
          nextCursor: 'cursor_2',
        },
      })
      .mockResolvedValueOnce({
        data: {
          conversations: [nextConversation satisfies AdminMessagingConversationSummary],
          nextCursor: null,
        },
      });

    const user = userEvent.setup();
    renderWithQueryClient(<MessagingConsole />);

    expect(await screen.findByText('list.nextPageAvailable')).toBeInTheDocument();
    await user.click(screen.getByTestId('messaging-load-more'));

    await waitFor(() => {
      expect(mockListAdminConversations).toHaveBeenCalledWith(
        expect.objectContaining({ cursor: 'cursor_2' }),
      );
    });
    expect((await screen.findAllByText('Second private thread')).length).toBeGreaterThan(0);
    expect(screen.getByText('list.endOfQueue')).toBeInTheDocument();
  });

  it('posts public replies and internal notes to separate messaging endpoints', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<MessagingConsole initialConversationRef="msg_20260531_0001" />);

    const publicComposer = await screen.findByTestId('messaging-public-reply-composer');
    await user.type(within(publicComposer).getByLabelText('reply.message'), 'Public answer.');
    fireEvent.submit(publicComposer);

    await waitFor(() => {
      expect(mockAddAdminMessage).toHaveBeenCalledWith(
        'msg_20260531_0001',
        expect.objectContaining({
          body: 'Public answer.',
          client_message_id: expect.any(String),
        }),
        expect.any(String),
      );
    });
    expect(mockAddAdminInternalNote).not.toHaveBeenCalled();

    const internalComposer = screen.getByTestId('messaging-internal-note-composer');
    await user.type(within(internalComposer).getByLabelText('internalNote.message'), 'Private note.');
    fireEvent.submit(internalComposer);

    await waitFor(() => {
      expect(mockAddAdminInternalNote).toHaveBeenCalledWith(
        'msg_20260531_0001',
        expect.objectContaining({
          body: 'Private note.',
          client_message_id: expect.any(String),
        }),
        expect.any(String),
      );
    });
  });

  it('keeps closed conversations read-only while exposing reopen', async () => {
    const closedConversation = buildConversation({
      closed_at: '2026-05-31T11:00:00Z',
      response_state: 'none',
      status: 'closed',
    });
    mockListAdminConversations.mockResolvedValue({
      data: {
        conversations: [closedConversation satisfies AdminMessagingConversationSummary],
        nextCursor: null,
      },
    });
    mockGetAdminConversation.mockResolvedValue({ data: closedConversation });

    renderWithQueryClient(<MessagingConsole initialConversationRef="msg_20260531_0001" />);

    const publicComposer = await screen.findByTestId('messaging-public-reply-composer');
    const internalComposer = screen.getByTestId('messaging-internal-note-composer');

    expect(within(publicComposer).getByLabelText('reply.message')).toBeDisabled();
    expect(within(internalComposer).getByLabelText('internalNote.message')).toBeDisabled();
    expect(screen.getByText('actions.closedReadOnly')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'actions.reopen' })).toBeInTheDocument();
  });
});
