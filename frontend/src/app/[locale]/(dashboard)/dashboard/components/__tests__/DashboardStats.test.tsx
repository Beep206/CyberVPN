import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { DashboardStats } from '../DashboardStats';

vi.mock('../../hooks/useDashboardData', () => ({
  useServerStats: vi.fn(),
  useSystemStats: vi.fn(),
  useBandwidthAnalytics: vi.fn(),
  useMonitoringRecap: vi.fn(),
}));

vi.mock('@/lib/api/usage', () => ({
  usageApi: {
    getMyUsage: vi.fn(),
  },
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

describe('DashboardStats', () => {
  beforeEach(async () => {
    vi.clearAllMocks();

    const hooks = await import('../../hooks/useDashboardData');
    const { usageApi } = await import('@/lib/api/usage');

    vi.mocked(hooks.useServerStats).mockReturnValue({
      data: { online: 8, total: 10 },
      isLoading: false,
    } as never);

    vi.mocked(hooks.useSystemStats).mockReturnValue({
      data: { active_users: 128 },
      isLoading: false,
    } as never);

    vi.mocked(hooks.useBandwidthAnalytics).mockReturnValue({
      data: { bytes_out: 512 * 1024 ** 3 },
      isLoading: false,
    } as never);

    vi.mocked(hooks.useMonitoringRecap).mockReturnValue({
      data: {
        total: {
          users: 2048,
          nodes: 18,
          traffic_bytes: 9 * 1024 ** 4,
          distinct_countries: 42,
        },
        this_month: {
          users: 120,
          traffic_bytes: 1024 ** 4,
        },
      },
      isLoading: false,
    } as never);

    vi.mocked(usageApi.getMyUsage).mockResolvedValue({
      data: {
        bandwidth_used_bytes: 2 * 1024 ** 3,
        bandwidth_limit_bytes: 10 * 1024 ** 3,
        connections_active: 3,
        connections_limit: 5,
        generated_at: '2026-04-24T10:00:05Z',
        last_connection_at: '2026-04-24T10:00:00Z',
        period_end: '2026-05-24T00:00:00Z',
        period_start: '2026-04-24T00:00:00Z',
        usage_available: true,
        usage_source: 'remnawave',
        usage_unavailable_reason: null,
      },
    } as never);
  });

  it('renders the recap card with users, nodes, traffic, and countries', () => {
    renderWithQueryClient(<DashboardStats />);

    expect(screen.getByText('networkRecap')).toBeInTheDocument();
    expect(screen.getByText('2,048')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
    expect(screen.getByText('9.0 TB')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText(/thisMonth: 120 \/ 1.0 TB/)).toBeInTheDocument();
  });

  it('marks VPN usage unavailable when backend has no authoritative snapshot', async () => {
    const { usageApi } = await import('@/lib/api/usage');
    vi.mocked(usageApi.getMyUsage).mockResolvedValueOnce({
      data: {
        bandwidth_used_bytes: 0,
        bandwidth_limit_bytes: 0,
        connections_active: 0,
        connections_limit: 0,
        generated_at: '2026-04-24T10:00:05Z',
        last_connection_at: null,
        period_end: '2026-04-24T10:00:05Z',
        period_start: '2026-04-24T10:00:05Z',
        usage_available: false,
        usage_source: 'unavailable',
        usage_unavailable_reason: 'upstream_unavailable',
      },
    } as never);

    renderWithQueryClient(<DashboardStats />);

    expect(await screen.findByText('Usage unavailable')).toBeInTheDocument();
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('--')).toBeInTheDocument();
  });
});
