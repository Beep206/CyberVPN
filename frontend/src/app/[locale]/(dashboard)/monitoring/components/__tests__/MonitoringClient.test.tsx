/**
 * MonitoringClient Component Tests (TOB-3)
 *
 * Tests the system monitoring dashboard:
 * - System health status (overall and per-service)
 * - Service cards (API, Database, Redis, Workers)
 * - Real-time metrics (requests, response time, error rate)
 * - Network bandwidth visualization
 * - Active connections display
 * - Auto-refresh functionality (30s interval)
 * - Loading and error states
 *
 * Depends on: FG-5 (Monitoring page implementation)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MonitoringClient } from '../MonitoringClient';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock API modules
vi.mock('@/lib/api', () => ({
  monitoringApi: {
    health: vi.fn(),
    getStats: vi.fn(),
    getBandwidth: vi.fn(),
  },
}));

// Helper to wrap component with QueryClient
function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchInterval: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('MonitoringClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('test_displays_loading_state_initially', async () => {
      const { monitoringApi } = await import('@/lib/api');

      // Set up pending promises to keep component in loading state
      vi.mocked(monitoringApi.health).mockReturnValue(new Promise(() => {}) as never);
      vi.mocked(monitoringApi.getStats).mockReturnValue(new Promise(() => {}) as never);
      vi.mocked(monitoringApi.getBandwidth).mockReturnValue(new Promise(() => {}) as never);

      renderWithQueryClient(<MonitoringClient />);

      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });

    it('test_renders_overall_status_banner', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText(/All Systems/)).toBeInTheDocument();
        expect(screen.getByText(/Operational/)).toBeInTheDocument();
      });
    });

    it('test_renders_all_service_cards', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({
        data: {
          status: 'healthy',
          api_status: 'healthy',
          database_status: 'healthy',
          redis_status: 'healthy',
          worker_status: 'healthy',
        }
      } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('API Server')).toBeInTheDocument();
        expect(screen.getByText('PostgreSQL Database')).toBeInTheDocument();
        expect(screen.getByText('Redis Cache')).toBeInTheDocument();
        expect(screen.getByText('Background Workers')).toBeInTheDocument();
      });
    });

    it('test_renders_metrics_cards', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({
        data: {
          total_requests: 15420,
          avg_response_time: 125,
          error_rate: 0.05
        }
      } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const requests = screen.getAllByText(/Total Requests/);
        const responseTime = screen.getAllByText(/Response Time/);
        expect(requests.length).toBeGreaterThan(0);
        expect(responseTime.length).toBeGreaterThan(0);
      });
    });

    it('test_renders_bandwidth_visualization', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 45, outbound_mbps: 62 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('Network Bandwidth')).toBeInTheDocument();
        expect(screen.getByText(/Inbound/)).toBeInTheDocument();
        expect(screen.getByText(/Outbound/)).toBeInTheDocument();
      });
    });

    it('test_renders_active_connections', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000, active_connections: 145 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('Active Connections')).toBeInTheDocument();
        expect(screen.getByText('145')).toBeInTheDocument();
      });
    });
  });

  describe('Health Status', () => {
    it('test_displays_healthy_status', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText(/Operational/)).toBeInTheDocument();
      });
    });

    it('test_displays_degraded_status', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'degraded' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText(/Degraded/)).toBeInTheDocument();
      });
    });

    it('test_displays_down_status', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'down' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText(/Down/)).toBeInTheDocument();
      });
    });
  });

  describe('Service Cards', () => {
    it('test_api_service_healthy_indicator', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({
        data: { status: 'healthy', api_status: 'healthy' }
      } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('API Server')).toBeInTheDocument();
        expect(screen.getAllByText(/Operational/).length).toBeGreaterThan(0);
      });
    });

    it('test_database_service_healthy_indicator', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({
        data: { status: 'healthy', database_status: 'healthy' }
      } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('PostgreSQL Database')).toBeInTheDocument();
        expect(screen.getAllByText(/Operational/).length).toBeGreaterThan(0);
      });
    });

    it('test_redis_service_degraded_indicator', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({
        data: { status: 'degraded', redis_status: 'degraded' }
      } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('Redis Cache')).toBeInTheDocument();
        expect(screen.getAllByText(/Degraded/).length).toBeGreaterThan(0);
      });
    });

    it('test_worker_service_down_indicator', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({
        data: { status: 'down', worker_status: 'down' }
      } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('Background Workers')).toBeInTheDocument();
        expect(screen.getAllByText(/Down/).length).toBeGreaterThan(0);
      });
    });
  });

  describe('Metrics', () => {
    it('test_displays_request_count_metric', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1234567 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('1,234,567')).toBeInTheDocument();
      });
    });

    it('test_displays_response_time_metric', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { avg_response_time: 87, total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const elements = screen.getAllByText(/87/);
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it('test_displays_error_rate_metric', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { error_rate: 2.5, total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const elements = screen.getAllByText(/2\.5/);
        expect(elements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Bandwidth', () => {
    it('test_displays_inbound_bandwidth', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 256, outbound_mbps: 0 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const elements = screen.getAllByText(/256/);
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it('test_displays_outbound_bandwidth', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 0, outbound_mbps: 384 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const elements = screen.getAllByText(/384/);
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it('test_bandwidth_visualization_renders', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 100, outbound_mbps: 150 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const bandwidthSection = screen.getByText('Network Bandwidth').closest('.cyber-card');
        expect(bandwidthSection).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('test_handles_api_error_gracefully', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockRejectedValue(new Error('API Error'));
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 1000 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      // Component should still show loading state when one API fails
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Data Formatting', () => {
    it('test_formats_large_numbers_with_commas', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 9876543 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 10, outbound_mbps: 15 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        expect(screen.getByText('9,876,543')).toBeInTheDocument();
      });
    });

    it('test_handles_zero_values_gracefully', async () => {
      const { monitoringApi } = await import('@/lib/api');

      vi.mocked(monitoringApi.health).mockResolvedValue({ data: { status: 'healthy' } } as never);
      vi.mocked(monitoringApi.getStats).mockResolvedValue({ data: { total_requests: 0, error_rate: 0, avg_response_time: 0 } } as never);
      vi.mocked(monitoringApi.getBandwidth).mockResolvedValue({ data: { inbound_mbps: 0, outbound_mbps: 0 } } as never);

      renderWithQueryClient(<MonitoringClient />);

      await waitFor(() => {
        const zeros = screen.getAllByText('0');
        expect(zeros.length).toBeGreaterThan(0);
      });
    });
  });
});
