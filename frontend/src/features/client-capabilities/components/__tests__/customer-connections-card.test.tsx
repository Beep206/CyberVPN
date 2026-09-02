import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ButtonHTMLAttributes, ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiMocks = vi.hoisted(() => ({
  dropCustomerConnections: vi.fn(),
  getCustomerConnections: vi.fn(),
  requestCustomerConnections: vi.fn(),
}));

const messages: Record<string, string> = {
  'activeIps': 'Active IP count',
  'connected': 'Connected',
  'connectedNodes': 'Connected nodes',
  'description': 'Privacy-safe connection summary.',
  'disconnected': 'Not connected',
  'drop': 'Disconnect my sessions',
  'dropAccepted': 'The disconnect request was accepted.',
  'dropFailedNoRetry': 'It was not retried automatically.',
  'dropUnknown': 'The provider outcome could not be confirmed.',
  'dropping': 'Disconnecting...',
  'errors.conflict': 'Conflict.',
  'errors.forbidden': 'This connection action is not available for your account.',
  'errors.generic': 'Connection status could not be loaded.',
  'errors.provider': 'The VPN provider rejected the operation.',
  'errors.unavailable': 'Connection controls are temporarily unavailable.',
  'eyebrow': 'LIVE CONNECTIONS',
  'failed': 'Connection check failed.',
  'idle': 'Connection data is requested only on demand.',
  'lastSeen': 'Last seen',
  'load': 'Check now',
  'never': 'No recent connection',
  'pending': 'Preparing a fresh connection snapshot...',
  'privacy': 'Only totals for your account are shown.',
  'refresh': 'Refresh',
  'refreshRequired': 'Refresh before sending another request.',
  'refreshing': 'Checking...',
  'status': 'Status',
  'title': 'Your current VPN connection',
};

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const template = key === 'progress'
      ? 'Checking nodes: {completed} of {total}'
      : messages[key] ?? key;
    return Object.entries(values ?? {}).reduce(
      (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
      template,
    );
  },
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({
    magnetic,
    touchTarget,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement> & {
    magnetic?: boolean;
    touchTarget?: string;
  }) => {
    void magnetic;
    void touchTarget;
    return <button {...props} />;
  },
}));

vi.mock('@/lib/api/remnawave-status', () => ({
  remnawaveStatusApi: apiMocks,
}));

import { CustomerConnectionsCard } from '../customer-connections-card';

const capabilities = {
  drop_connections: true,
  drop_outcome_may_be_unknown: true,
  drop_requires_idempotency_key: true,
  read_connections: true,
};

const completedStatus = {
  active_ip_count: 2,
  capabilities,
  connected: true,
  connected_node_count: 1,
  is_completed: true,
  is_failed: false,
  last_seen_at: '2026-08-31T08:00:00Z',
  progress: { completed: 2, percent: 100, total: 2 },
  success: true,
};

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('CustomerConnectionsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.requestCustomerConnections.mockResolvedValue({
      capabilities,
      expires_in_seconds: 300,
      poll_after_seconds: 1,
      request_id: 'a'.repeat(43),
    });
    apiMocks.getCustomerConnections.mockResolvedValue(completedStatus);
    apiMocks.dropCustomerConnections.mockResolvedValue({
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 86_400,
      receipt_id: 'b'.repeat(43),
      requires_reconciliation: false,
      retry_allowed: false,
      state: 'accepted',
    });
  });

  it('does not fetch until requested and renders only own-scope aggregates', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<CustomerConnectionsCard surface="dashboard" />);

    expect(apiMocks.requestCustomerConnections).not.toHaveBeenCalled();
    expect(screen.getByText('Connection data is requested only on demand.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Check now' }));

    expect(await screen.findByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('Connected nodes')).toBeInTheDocument();
    expect(screen.getByText('Active IP count')).toBeInTheDocument();
    expect(screen.getByText('Only totals for your account are shown.')).toBeInTheDocument();
    expect(screen.queryByText('203.0.113.9')).not.toBeInTheDocument();
    expect(screen.queryByText('private-node-1')).not.toBeInTheDocument();
    expect(apiMocks.requestCustomerConnections).toHaveBeenCalledTimes(1);
    expect(apiMocks.getCustomerConnections).toHaveBeenCalledWith('a'.repeat(43));
  });

  it('submits one idempotent drop and disables resubmission until refresh', async () => {
    const user = userEvent.setup();
    apiMocks.dropCustomerConnections.mockResolvedValueOnce({
      expires_at: null,
      expires_in_seconds: null,
      receipt_id: 'c'.repeat(43),
      requires_reconciliation: true,
      retry_allowed: false,
      state: 'outcome_unknown',
    });
    renderWithQueryClient(<CustomerConnectionsCard surface="miniapp" />);

    await user.click(screen.getByRole('button', { name: 'Check now' }));
    const dropButton = await screen.findByRole('button', { name: 'Disconnect my sessions' });
    await user.click(dropButton);

    await waitFor(() => expect(apiMocks.dropCustomerConnections).toHaveBeenCalledTimes(1));
    expect(apiMocks.dropCustomerConnections.mock.calls[0]?.[0]).toEqual(expect.any(String));
    expect(await screen.findByText(/provider outcome could not be confirmed/i)).toBeInTheDocument();
    expect(dropButton).toBeDisabled();
  });

  it('maps forbidden responses without exposing provider details', async () => {
    const user = userEvent.setup();
    apiMocks.requestCustomerConnections.mockRejectedValueOnce({
      response: {
        data: { detail: 'private upstream topology and credential' },
        status: 403,
      },
    });
    renderWithQueryClient(<CustomerConnectionsCard surface="dashboard" />);

    await user.click(screen.getByRole('button', { name: 'Check now' }));

    expect(
      await screen.findByText('This connection action is not available for your account.'),
    ).toBeInTheDocument();
    expect(screen.queryByText(/private upstream topology/i)).not.toBeInTheDocument();
  });
});
