import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AdminRemnawaveCapabilitiesAndStreams } from '@/lib/api/remnawave-status';

const { getCapabilitiesAndStreams, getNodeDiagnostics } = vi.hoisted(() => ({
  getCapabilitiesAndStreams: vi.fn(),
  getNodeDiagnostics: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (
    key: string,
    values?: Record<string, string | number>,
  ) => values ? `${key}:${Object.values(values).join(':')}` : key,
}));

vi.mock('@/lib/api/remnawave-status', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-status')>();
  return {
    ...actual,
    adminRemnawaveStatusApi: {
      getCapabilitiesAndStreams,
      getNodeDiagnostics,
    },
  };
});

import { RemnawaveOperationsConsole } from './remnawave-operations-console';

const healthyResponse: AdminRemnawaveCapabilitiesAndStreams = {
  panel_version: '3.4.3',
  target_panel_version: '3.4.3',
  target_node_version: '3.4.1',
  contract_version: '3.4.13',
  capabilities: {
    numeric_user_ids: true,
    connections: true,
    geo_check: true,
    node_integrations: true,
    shared_lists: true,
    node_ssh: true,
    tags: true,
    host_mapper: true,
    root_snippets: true,
    redis_stream_export: true,
  },
  streams: [
    {
      key: 'user_usage',
      retention_days: 7,
      consumer_group: 'cybervpn-user-usage',
      status: 'healthy',
      lag: 0,
      pending: 0,
      dead_letters: 0,
      last_consumed_at: '2026-08-30T08:00:00Z',
      degraded_reason: null,
    },
  ],
  degraded_reason: null,
};

function renderConsole() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RemnawaveOperationsConsole />
    </QueryClientProvider>,
  );
}

describe('RemnawaveOperationsConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCapabilitiesAndStreams.mockResolvedValue({ data: healthyResponse });
    getNodeDiagnostics.mockResolvedValue({
      data: {
        nodes: [],
        metrics_source: 'remnawave_api',
        updated_at: '2026-08-30T08:00:00Z',
        token_rotation_required: false,
      },
    });
  });

  it('renders an accessible loading state before the snapshot resolves', () => {
    getCapabilitiesAndStreams.mockReturnValue(new Promise(() => undefined));

    renderConsole();

    expect(screen.getByRole('status')).toHaveTextContent('loading');
  });

  it('shows only the safe capability inventory and operational stream health', async () => {
    getCapabilitiesAndStreams.mockResolvedValue({
      data: {
        ...healthyResponse,
        node_ip: '203.0.113.55',
        ssh_ticket: 'secret-terminal-ticket',
        streams: [
          {
            ...healthyResponse.streams[0],
            status: 'degraded',
            lag: 24,
            degraded_reason: 'consumer lag exceeded threshold',
          },
        ],
      },
    });

    renderConsole();

    expect(await screen.findByText('capabilities.items.node_ssh.title')).toBeInTheDocument();
    expect(screen.getByText('streams.items.user_usage')).toBeInTheDocument();
    expect(screen.getByText('consumer lag exceeded threshold')).toBeInTheDocument();
    expect(screen.queryByText('203.0.113.55')).not.toBeInTheDocument();
    expect(screen.queryByText('secret-terminal-ticket')).not.toBeInTheDocument();
  });

  it('renders explicit empty capability and stream states', async () => {
    getCapabilitiesAndStreams.mockResolvedValue({
      data: {
        ...healthyResponse,
        capabilities: Object.fromEntries(
          Object.keys(healthyResponse.capabilities).map((key) => [key, false]),
        ),
        streams: [],
      },
    });

    renderConsole();

    expect(await screen.findByText('capabilities.empty')).toBeInTheDocument();
    expect(screen.getByText('streams.empty')).toBeInTheDocument();
  });

  it('renders a permission boundary for 403 without retrying the request', async () => {
    getCapabilitiesAndStreams.mockRejectedValue({ response: { status: 403 } });

    renderConsole();

    expect(await screen.findByRole('alert')).toHaveTextContent('forbidden.title');
    expect(getCapabilitiesAndStreams).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'retry' })).toBeDisabled();
  });

  it('lets an operator retry a transient failure', async () => {
    getCapabilitiesAndStreams
      .mockRejectedValueOnce(new Error('temporary failure'))
      .mockResolvedValueOnce({ data: healthyResponse });
    const user = userEvent.setup();

    renderConsole();

    expect(await screen.findByRole('alert')).toHaveTextContent('error.title');
    await user.click(screen.getAllByRole('button', { name: 'retry' })[1]!);

    await waitFor(() => {
      expect(getCapabilitiesAndStreams).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText('capabilities.items.connections.title')).toBeInTheDocument();
  });
});
