/**
 * AnalyticsClient Component Tests (TOB-3)
 *
 * Tests the analytics dashboard:
 * - Data fetching from payments, usage, and subscriptions APIs
 * - Time range selector (7d, 30d, 90d)
 * - Revenue, users, and bandwidth stat cards
 * - Revenue trend chart rendering
 * - Subscription distribution visualization
 * - 24h bandwidth usage chart
 * - Loading states and error handling
 *
 * Depends on: FG-4 (Analytics page implementation)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AnalyticsClient } from '../AnalyticsClient';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock API modules
vi.mock('@/lib/api', () => ({
  paymentsApi: {
    getHistory: vi.fn(),
  },
  usageApi: {
    getMyUsage: vi.fn(),
  },
  subscriptionsApi: {
    list: vi.fn(),
  },
}));

// Helper to wrap component with QueryClient
function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('AnalyticsClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('test_displays_loading_state_initially', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      // Set up pending promises to keep component in loading state
      vi.mocked(paymentsApi.getHistory).mockReturnValue(new Promise(() => {}) as any);
      vi.mocked(usageApi.getMyUsage).mockReturnValue(new Promise(() => {}) as any);
      vi.mocked(subscriptionsApi.list).mockReturnValue(new Promise(() => {}) as any);

      renderWithQueryClient(<AnalyticsClient />);

      // Find spinner by its animation class
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });

    it('test_renders_time_range_selector', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('7 Days')).toBeInTheDocument();
        expect(screen.getByText('30 Days')).toBeInTheDocument();
        expect(screen.getByText('90 Days')).toBeInTheDocument();
      });
    });

    it('test_renders_revenue_stat_card', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({
        data: [
          { amount: 29.99, created_at: '2025-01-01T00:00:00Z' },
          { amount: 19.99, created_at: '2025-01-02T00:00:00Z' },
        ]
      } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 100 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('Total Revenue')).toBeInTheDocument();
        expect(screen.getByText('$49.98')).toBeInTheDocument();
      });
    });

    it('test_renders_users_stat_cards', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('Total Users')).toBeInTheDocument();
        expect(screen.getByText('Active Users')).toBeInTheDocument();
      });
    });

    it('test_renders_bandwidth_stat_card', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 5000 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('Total Bandwidth')).toBeInTheDocument();
        expect(screen.getByText('5.0 TB')).toBeInTheDocument();
      });
    });
  });

  describe('API Integration', () => {
    it('test_fetches_payments_history_on_mount', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(paymentsApi.getHistory).toHaveBeenCalled();
      });
    });

    it('test_fetches_usage_data_on_mount', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(usageApi.getMyUsage).toHaveBeenCalled();
      });
    });

    it('test_fetches_subscriptions_on_mount', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(subscriptionsApi.list).toHaveBeenCalled();
      });
    });
  });

  describe('Revenue Chart', () => {
    it('test_displays_revenue_chart_with_data', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({
        data: [
          { amount: 29.99, created_at: '2025-01-01T00:00:00Z' },
          { amount: 19.99, created_at: '2025-01-02T00:00:00Z' },
        ]
      } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('Revenue Trend')).toBeInTheDocument();
      });
    });

    it('test_calculates_total_revenue_correctly', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({
        data: [
          { amount: 100, created_at: '2025-01-01T00:00:00Z' },
          { amount: 200, created_at: '2025-01-02T00:00:00Z' },
          { amount: 150, created_at: '2025-01-03T00:00:00Z' },
        ]
      } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('$450.00')).toBeInTheDocument();
      });
    });
  });

  describe('Subscription Distribution', () => {
    it('test_displays_subscription_distribution_chart', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({
        data: [
          { plan_name: 'Basic', id: 1 },
          { plan_name: 'Pro', id: 2 },
          { plan_name: 'Basic', id: 3 },
        ]
      } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('Subscription Distribution')).toBeInTheDocument();
        expect(screen.getByText('Basic')).toBeInTheDocument();
        expect(screen.getByText('Pro')).toBeInTheDocument();
      });
    });

    it('test_calculates_subscription_percentages', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({
        data: [
          { plan_name: 'Basic', id: 1 },
          { plan_name: 'Basic', id: 2 },
          { plan_name: 'Pro', id: 3 },
          { plan_name: 'Pro', id: 4 },
        ]
      } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        const percentages = screen.getAllByText(/50\.0%/);
        expect(percentages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Bandwidth Chart', () => {
    it('test_displays_24h_bandwidth_chart', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 1000 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('24h Bandwidth Usage')).toBeInTheDocument();
      });
    });

    it('test_converts_bandwidth_gb_to_tb', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 3500 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('3.5 TB')).toBeInTheDocument();
      });
    });
  });

  describe('Time Range Selector', () => {
    it('test_changes_time_range_on_button_click', async () => {
      const user = userEvent.setup({ delay: null });
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      let callCount = 0;
      vi.mocked(paymentsApi.getHistory).mockImplementation(async () => {
        callCount++;
        return { data: [] } as any;
      });
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('7 Days')).toBeInTheDocument();
      });

      const initialCallCount = callCount;
      const sevenDaysButton = screen.getByText('7 Days');
      await user.click(sevenDaysButton);

      // Verify the API was called again after clicking (indicating state change)
      await waitFor(() => {
        expect(callCount).toBeGreaterThan(initialCallCount);
      });
    });

    it('test_default_time_range_is_30_days', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        const thirtyDaysButton = screen.getByText('30 Days');
        expect(thirtyDaysButton).toHaveClass('bg-neon-cyan/20');
      });
    });
  });

  describe('Error Handling', () => {
    it('test_shows_loading_when_api_call_fails', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      // Mock one API to reject
      vi.mocked(paymentsApi.getHistory).mockRejectedValue(new Error('API Error'));
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      // Component should still show loading state when one API fails
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Data Formatting', () => {
    it('test_formats_currency_correctly', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({
        data: [
          { amount: 1234.56, created_at: '2025-01-01T00:00:00Z' },
        ]
      } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        const formatted = screen.getAllByText('$1,234.56');
        expect(formatted.length).toBeGreaterThan(0);
      });
    });

    it('test_handles_zero_values_gracefully', async () => {
      const { paymentsApi, usageApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(paymentsApi.getHistory).mockResolvedValue({ data: [] } as any);
      vi.mocked(usageApi.getMyUsage).mockResolvedValue({ data: { bandwidth_used_gb: 0 } } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithQueryClient(<AnalyticsClient />);

      await waitFor(() => {
        expect(screen.getByText('$0.00')).toBeInTheDocument();
        expect(screen.getByText('0.0 TB')).toBeInTheDocument();
      });
    });
  });
});
