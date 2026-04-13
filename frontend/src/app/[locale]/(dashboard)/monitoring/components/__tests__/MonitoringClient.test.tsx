import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { MonitoringClient } from '../MonitoringClient';

vi.mock('@/lib/api', () => ({
  monitoringApi: {
    health: vi.fn(),
    getStats: vi.fn(),
    getBandwidth: vi.fn(),
    getMetadata: vi.fn(),
    getRecap: vi.fn(),
  },
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchInterval: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

const DEFAULT_HEALTH = {
  status: 'healthy',
  timestamp: '2026-04-12T10:00:00Z',
  components: {
    remnawave: {
      status: 'healthy',
      message: 'Remnawave API connection successful',
      response_time_ms: 42,
    },
    database: {
      status: 'healthy',
      message: 'Database connection successful',
      response_time_ms: 12,
    },
    redis: {
      status: 'healthy',
      message: 'Redis connection successful',
      response_time_ms: 8,
    },
  },
};

const DEFAULT_STATS = {
  total_users: 2048,
  active_users: 145,
  total_servers: 12,
  online_servers: 10,
  total_traffic_bytes: 9 * 1024 ** 4,
};

const DEFAULT_BANDWIDTH = {
  bytes_in: 0,
  bytes_out: 512 * 1024 ** 3,
  period: 'today',
};

const DEFAULT_METADATA = {
  version: '2.7.4',
  build: {
    time: '2026-03-30T12:00:00Z',
    number: '4274',
  },
  git: {
    backend: {
      commit_sha: 'abcdef1234567890',
      branch: 'main',
      commit_url: 'https://example.com/backend/commit',
    },
    frontend: {
      commit_sha: 'fedcba0987654321',
      commit_url: 'https://example.com/frontend/commit',
    },
  },
  timestamp: '2026-04-12T10:00:00Z',
};

const DEFAULT_RECAP = {
  version: '2.7.4',
  init_date: '2026-01-01T00:00:00Z',
  total: {
    users: 2048,
    nodes: 18,
    traffic_bytes: 9 * 1024 ** 4,
    nodes_ram: '1024 GB',
    nodes_cpu_cores: 64,
    distinct_countries: 42,
  },
  this_month: {
    users: 120,
    traffic_bytes: 1024 ** 4,
  },
  timestamp: '2026-04-12T10:00:00Z',
};

async function mockMonitoringApi({
  health = DEFAULT_HEALTH,
  stats = DEFAULT_STATS,
  bandwidth = DEFAULT_BANDWIDTH,
  metadata = DEFAULT_METADATA,
  recap = DEFAULT_RECAP,
}: {
  health?: typeof DEFAULT_HEALTH;
  stats?: typeof DEFAULT_STATS;
  bandwidth?: typeof DEFAULT_BANDWIDTH;
  metadata?: typeof DEFAULT_METADATA;
  recap?: typeof DEFAULT_RECAP;
} = {}) {
  const { monitoringApi } = await import('@/lib/api');

  vi.mocked(monitoringApi.health).mockResolvedValue({ data: health } as never);
  vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: stats } as never);
  vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: bandwidth } as never);
  vi.mocked(monitoringApi.getMetadata).mockResolvedValue({ data: metadata } as never);
  vi.mocked(monitoringApi.getRecap).mockResolvedValue({ data: recap } as never);
}

describe('MonitoringClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state while monitoring queries are pending', async () => {
    const { monitoringApi } = await import('@/lib/api');

    vi.mocked(monitoringApi.health).mockReturnValue(new Promise(() => {}) as never);
    vi.mocked(monitoringApi.getStats).mockReturnValue(new Promise(() => {}) as never);
    vi.mocked(monitoringApi.getBandwidth).mockReturnValue(new Promise(() => {}) as never);
    vi.mocked(monitoringApi.getMetadata).mockReturnValue(new Promise(() => {}) as never);
    vi.mocked(monitoringApi.getRecap).mockReturnValue(new Promise(() => {}) as never);

    renderWithQueryClient(<MonitoringClient />);

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders health banner, service cards, and metadata baseline', async () => {
    await mockMonitoringApi();

    renderWithQueryClient(<MonitoringClient />);

    await waitFor(() => {
      expect(screen.getByText(/All Systems Operational/)).toBeInTheDocument();
      expect(screen.getByText('Remnawave API')).toBeInTheDocument();
      expect(screen.getByText('PostgreSQL Database')).toBeInTheDocument();
      expect(screen.getByText('Redis Cache')).toBeInTheDocument();
      expect(screen.getByText('Panel Version')).toBeInTheDocument();
      expect(screen.getByText('Backend Git')).toBeInTheDocument();
      expect(screen.getByText('Frontend Git')).toBeInTheDocument();
      expect(screen.getByText('Remnawave Recap')).toBeInTheDocument();
    });
  });

  it('renders recap totals and live activity metrics', async () => {
    await mockMonitoringApi();

    renderWithQueryClient(<MonitoringClient />);

    await waitFor(() => {
      expect(screen.getAllByText('2.7.4').length).toBeGreaterThan(0);
      expect(screen.getByText('2,048')).toBeInTheDocument();
      expect(screen.getByText('18')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('145')).toBeInTheDocument();
      expect(screen.getByText('10 / 12')).toBeInTheDocument();
      expect(screen.getByText('512 GB')).toBeInTheDocument();
      expect(screen.getByText('9.0 TB')).toBeInTheDocument();
    });
  });

  it('renders degraded overall status when health endpoint is degraded', async () => {
    await mockMonitoringApi({
      health: {
        ...DEFAULT_HEALTH,
        status: 'degraded',
      },
    });

    renderWithQueryClient(<MonitoringClient />);

    await waitFor(() => {
      expect(screen.getByText(/All Systems Degraded/)).toBeInTheDocument();
    });
  });

  it('renders unhealthy component details when a service fails', async () => {
    await mockMonitoringApi({
      health: {
        ...DEFAULT_HEALTH,
        status: 'unhealthy',
        components: {
          ...DEFAULT_HEALTH.components,
          redis: {
            status: 'unhealthy',
            message: 'Redis connection failed',
            response_time_ms: 0,
          },
        },
      },
    });

    renderWithQueryClient(<MonitoringClient />);

    await waitFor(() => {
      expect(screen.getByText(/All Systems Unavailable/)).toBeInTheDocument();
      expect(screen.getByText('Redis connection failed')).toBeInTheDocument();
      expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
    });
  });
});
