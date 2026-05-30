import type React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SupportTicketsClient } from '../SupportTicketsClient';
import { SupportTicketsRoute } from '../SupportTicketsRoute';

const messages = vi.hoisted(() => ({
  actions: {
    close: 'Close ticket',
    refreshList: 'Refresh ticket list',
    reopen: 'Reopen ticket',
  },
  categories: {
    account: 'Account',
    billing: 'Billing',
    other: 'Other',
    privacy: 'Privacy',
    setup: 'Setup',
    status: 'Service status',
    vpn_access: 'VPN access',
  },
  description: 'Create, reply, close, and reopen tickets.',
  detail: {
    closedDescription: 'Reopen the ticket if the issue returned.',
    closedTitle: 'Ticket is closed',
    conversationTitle: 'Conversation',
    customerAuthor: 'You',
    emptyDescription: 'Ticket details appear here.',
    emptyTitle: 'Select a ticket',
    noMessages: 'No public messages are attached.',
    supportAuthor: 'Support',
  },
  errors: {
    close: 'Ticket close failed.',
    create: 'Ticket creation failed.',
    detail: 'Ticket detail failed.',
    list: 'Ticket list failed.',
    reopen: 'Ticket reopen failed.',
    reply: 'Reply failed.',
  },
  eyebrow: 'SUPPORT LINK',
  filters: {
    all: 'All tickets',
    statusLabel: 'Filter tickets by status',
  },
  form: {
    categoryLabel: 'Category',
    messageHelp: '{count}/4000 characters.',
    messageLabel: 'Message',
    messagePlaceholder: 'Describe the issue.',
    subjectLabel: 'Subject',
    subjectPlaceholder: 'Short summary',
    submit: 'Create ticket',
    submitting: 'Creating...',
    title: 'Create ticket',
  },
  list: {
    emptyDescription: 'Create a ticket when you need help.',
    emptyTitle: 'No tickets yet',
    openTicket: 'Open ticket {id}',
    title: 'My tickets',
  },
  reply: {
    label: 'Reply',
    placeholder: 'Add a safe update.',
    submit: 'Send reply',
    submitting: 'Sending...',
  },
  sensitiveWarning: {
    description: 'Never include passwords or raw VPN config files.',
    title: 'Do not send secrets',
  },
  status: {
    closed: 'Closed',
    open: 'Open',
    pending_customer: 'Customer reply due',
    pending_support: 'Support reply due',
    resolved: 'Resolved',
  },
  surface: {
    dashboard: 'Customer cabinet',
    miniapp: 'Telegram Mini App',
  },
  title: 'Support tickets',
}));

const apiMocks = vi.hoisted(() => ({
  close: vi.fn(),
  create: vi.fn(),
  get: vi.fn(),
  list: vi.fn(),
  reopen: vi.fn(),
  reply: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const value = key.split('.').reduce<unknown>((current, part) => {
      if (current && typeof current === 'object' && part in current) {
        return (current as Record<string, unknown>)[part];
      }

      return undefined;
    }, messages);
    const template = typeof value === 'string' ? value : key;

    if (!values) {
      return template;
    }

    return Object.entries(values).reduce(
      (result, [name, replacement]) => result.replaceAll(`{${name}}`, String(replacement)),
      template,
    );
  },
}));

vi.mock('@/lib/api/support-tickets', () => ({
  supportTicketsApi: apiMocks,
}));

function renderWithProviders(ui: React.ReactElement) {
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

const ticketSummary = {
  public_id: 'SUP-20260529-010',
  status: 'pending_support',
  category: 'vpn_access',
  priority: 'normal',
  subject: 'VPN cannot connect',
  last_message_preview: 'The app shows a safe timeout message.',
  created_at: '2026-05-29T13:20:00Z',
  updated_at: '2026-05-29T13:21:00Z',
  last_customer_message_at: '2026-05-29T13:20:00Z',
  last_support_message_at: null,
  resolved_at: null,
  closed_at: null,
};

const ticketDetail = {
  ...ticketSummary,
  messages: [
    {
      author_label: 'customer',
      body: 'The app shows a safe timeout message.',
      created_at: '2026-05-29T13:20:00Z',
    },
    {
      author_label: 'support',
      body: 'We are checking the access channel.',
      created_at: '2026-05-29T13:21:00Z',
    },
  ],
  events: [],
};

describe('SupportTicketsClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.list.mockResolvedValue({
      data: {
        nextCursor: null,
        tickets: [ticketSummary],
      },
    });
    apiMocks.get.mockResolvedValue({ data: ticketDetail });
    apiMocks.create.mockResolvedValue({
      data: {
        ...ticketSummary,
        public_id: 'SUP-20260529-011',
        subject: 'Payment confirmed but VPN missing',
        messages: [],
        events: [],
      },
    });
    apiMocks.reply.mockResolvedValue({
      data: {
        ...ticketDetail,
        last_message_preview: 'Here is a safe follow-up.',
        messages: [
          ...ticketDetail.messages,
          {
            author_label: 'customer',
            body: 'Here is a safe follow-up.',
            created_at: '2026-05-29T13:22:00Z',
          },
        ],
      },
    });
    apiMocks.close.mockResolvedValue({
      data: {
        ...ticketDetail,
        closed_at: '2026-05-29T13:23:00Z',
        status: 'closed',
      },
    });
    apiMocks.reopen.mockResolvedValue({
      data: {
        ...ticketDetail,
        closed_at: null,
        status: 'pending_support',
      },
    });
  });

  it('renders existing tickets, detail, and the sensitive-data warning', async () => {
    renderWithProviders(<SupportTicketsClient variant="dashboard" />);

    expect(screen.getByText('Do not send secrets')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('VPN cannot connect')).toBeInTheDocument();
    });

    expect(await screen.findByText('We are checking the access channel.')).toBeInTheDocument();
    expect(apiMocks.list).toHaveBeenCalledWith({ limit: 50, status: undefined });
    expect(apiMocks.get).toHaveBeenCalledWith('SUP-20260529-010');
  });

  it('renders from a route boundary when the parent layout provider is absent', async () => {
    render(<SupportTicketsRoute variant="dashboard" />);

    expect(screen.getByText('Do not send secrets')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('VPN cannot connect')).toBeInTheDocument();
    });

    expect(await screen.findByText('We are checking the access channel.')).toBeInTheDocument();
  });

  it('creates a ticket without sending a source field', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SupportTicketsClient variant="miniapp" />);

    await user.selectOptions(screen.getByLabelText('Category'), 'billing');
    await user.type(
      screen.getByLabelText('Subject'),
      'Payment confirmed but VPN missing',
    );
    await user.type(
      screen.getByLabelText('Message'),
      'Payment is final but the VPN profile is still missing.',
    );
    await user.click(screen.getByRole('button', { name: 'Create ticket' }));

    await waitFor(() => {
      expect(apiMocks.create).toHaveBeenCalledWith({
        category: 'billing',
        message: 'Payment is final but the VPN profile is still missing.',
        priority: 'normal',
        subject: 'Payment confirmed but VPN missing',
      });
    });
  });

  it('adds a reply, closes, and reopens the selected ticket', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SupportTicketsClient variant="dashboard" />);

    await screen.findByText('We are checking the access channel.');

    await user.type(screen.getByLabelText('Reply'), 'Here is a safe follow-up.');
    await user.click(screen.getByRole('button', { name: 'Send reply' }));

    await waitFor(() => {
      expect(apiMocks.reply).toHaveBeenCalledWith('SUP-20260529-010', {
        message: 'Here is a safe follow-up.',
      });
    });

    await user.click(screen.getByRole('button', { name: 'Close ticket' }));

    await waitFor(() => {
      expect(apiMocks.close).toHaveBeenCalledWith('SUP-20260529-010');
    });

    await user.click(await screen.findByRole('button', { name: 'Reopen ticket' }));

    await waitFor(() => {
      expect(apiMocks.reopen).toHaveBeenCalledWith('SUP-20260529-010');
    });
  });
});
