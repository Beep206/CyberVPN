import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GlobalMetricsHud } from '../global-metrics-hud';

const { getOverviewMock } = vi.hoisted(() => ({
  getOverviewMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string) => {
    const labels: Record<string, string> = {
      'labels.totalBandwidth': 'Monthly Traffic',
      'labels.activeNodes': 'Online Servers',
      'labels.threatsIntercepted': 'Live Users',
    };

    return labels[key] ?? key;
  },
}));

vi.mock('@/lib/api', () => ({
  publicNetworkApi: {
    getOverview: getOverviewMock,
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('GlobalMetricsHud', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders truthful public overview metrics from the dedicated API', async () => {
    getOverviewMock.mockResolvedValue({
      data: {
        schemaVersion: 'public-network-overview.v1',
        generatedAt: '2026-04-22T12:00:00Z',
        expiresAt: '2026-04-22T12:01:00Z',
        freshnessStatus: 'fresh',
        global: {
          status: 'online',
          totalUsers: 1120,
          activeUsers: 278,
          totalServers: 24,
          onlineServers: 24,
          totalNodes: 24,
          distinctCountries: 8,
          totalTrafficBytes: 5 * 1024 ** 4,
          monthlyTrafficBytes: 5 * 1024 ** 4,
          todayBytesIn: 0,
          todayBytesOut: 0,
        },
      },
    });

    render(<GlobalMetricsHud />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('5 TB')).toBeInTheDocument();
    });

    expect(getOverviewMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Monthly Traffic')).toBeInTheDocument();
    expect(screen.getByText('24')).toBeInTheDocument();
    expect(screen.getByText('278')).toBeInTheDocument();
  });
});
