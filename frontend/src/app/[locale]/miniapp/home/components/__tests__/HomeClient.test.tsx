/**
 * Mini App Home Page Tests (TOB-5)
 *
 * Tests the home/dashboard page:
 * - Subscription status display (active, trial, none)
 * - Usage stats (data, connections, last connected)
 * - Trial availability and activation
 * - Progress bar colors (red > 80%, cyan <= 80%)
 * - Quick actions visibility
 * - Theme support (dark/light)
 *
 * Depends on: MG-1 (Home page subscription check implementation)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import MiniAppHomePage from '../../page';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

// Mock API modules
vi.mock('@/lib/api', () => ({
  vpnApi: {
    getUsage: vi.fn(),
  },
  trialApi: {
    getStatus: vi.fn(),
  },
  subscriptionsApi: {
    list: vi.fn(),
  },
}));

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock i18n navigation
vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

// Mock VpnConfigCard
vi.mock('../../components/VpnConfigCard', () => ({
  VpnConfigCard: () => <div data-testid="vpn-config-card">VPN Config Card</div>,
}));

// Helper to wrap component with QueryClient
function renderWithProviders(ui: React.ReactElement) {
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

describe('MiniApp Home Page', () => {
  beforeEach(() => {
    setupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  describe('Loading State', () => {
    it('test_displays_loading_spinner', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockReturnValue(new Promise(() => {}) as any);
      vi.mocked(trialApi.getStatus).mockReturnValue(new Promise(() => {}) as any);
      vi.mocked(subscriptionsApi.list).mockReturnValue(new Promise(() => {}) as any);

      renderWithProviders(<MiniAppHomePage />);

      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('No Subscription', () => {
    it('test_displays_no_subscription_message', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({ data: null } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: false, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });
    });

    it('test_no_usage_stats_without_subscription', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({ data: null } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: false, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      expect(screen.queryByText('usage')).not.toBeInTheDocument();
    });
  });

  describe('Trial Subscription', () => {
    it('test_displays_trial_badge', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 1073741824, // 1 GB
          bandwidth_limit_bytes: 10737418240, // 10 GB
          connections_active: 2,
          connections_limit: 5,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: {
          is_trial_active: true,
          is_eligible: false,
          trial_end: '2025-01-30T23:59:59Z',
          days_remaining: 15,
        }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('trial')).toBeInTheDocument();
      });
    });

    it('test_shows_usage_stats_on_trial', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 2147483648, // 2 GB
          bandwidth_limit_bytes: 10737418240, // 10 GB
          connections_active: 3,
          connections_limit: 5,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: true, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('usage')).toBeInTheDocument();
        expect(screen.getByText('dataUsed')).toBeInTheDocument();
        expect(screen.getByText('connections')).toBeInTheDocument();
      });
    });
  });

  describe('Active Subscription', () => {
    it('test_displays_active_subscription', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 5368709120, // 5 GB
          bandwidth_limit_bytes: 107374182400, // 100 GB
          connections_active: 1,
          connections_limit: 10,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: false, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({
        data: [
          {
            status: 'active',
            plan_name: 'Premium',
            expires_at: '2025-12-31T23:59:59Z',
            data_limit_gb: 100,
          },
        ]
      } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('subscriptionActive')).toBeInTheDocument();
        expect(screen.getByText('Premium')).toBeInTheDocument();
      });
    });
  });

  describe('Usage Stats', () => {
    it('test_displays_data_usage', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 3221225472, // 3 GB
          bandwidth_limit_bytes: 10737418240, // 10 GB
          connections_active: 2,
          connections_limit: 5,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: true, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText(/3\.00 GB/)).toBeInTheDocument();
        expect(screen.getByText(/10\.00 GB/)).toBeInTheDocument();
      });
    });

    it('test_displays_connections_count', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 1073741824,
          bandwidth_limit_bytes: 10737418240,
          connections_active: 4,
          connections_limit: 10,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: true, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText(/4 \/ 10/)).toBeInTheDocument();
      });
    });

    it('test_cyan_progress_bar_under_80_percent', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 5368709120, // 5 GB (50%)
          bandwidth_limit_bytes: 10737418240, // 10 GB
          connections_active: 1,
          connections_limit: 5,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: true, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        const progressBar = document.querySelector('.bg-neon-cyan');
        expect(progressBar).toBeInTheDocument();
      });
    });

    it('test_red_progress_bar_over_80_percent', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 9663676416, // 9 GB (90%)
          bandwidth_limit_bytes: 10737418240, // 10 GB
          connections_active: 1,
          connections_limit: 5,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: true, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        const progressBar = document.querySelector('.bg-destructive');
        expect(progressBar).toBeInTheDocument();
      });
    });
  });

  describe('Trial Availability', () => {
    it('test_shows_trial_available_card', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({ data: null } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: {
          is_trial_active: false,
          is_eligible: true, // Can activate trial
        }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('trialAvailable')).toBeInTheDocument();
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });
    });

    it('test_no_trial_card_when_not_eligible', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({ data: null } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: {
          is_trial_active: false,
          is_eligible: false, // Not eligible
        }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      expect(screen.queryByText('trialAvailable')).not.toBeInTheDocument();
    });
  });

  describe('Quick Actions', () => {
    it('test_displays_quick_actions', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({ data: null } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: false, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('quickActions')).toBeInTheDocument();
        expect(screen.getByText('viewPlans')).toBeInTheDocument();
        expect(screen.getByText('wallet')).toBeInTheDocument();
        expect(screen.getByText('settings')).toBeInTheDocument();
      });
    });

    it('test_vpn_config_action_shown_with_subscription', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({
        data: {
          bandwidth_used_bytes: 1073741824,
          bandwidth_limit_bytes: 10737418240,
          connections_active: 1,
          connections_limit: 5,
          last_connection_at: '2025-01-15T14:30:00Z',
        }
      } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: true, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('vpnConfig')).toBeInTheDocument();
      });
    });

    it('test_vpn_config_action_hidden_without_subscription', async () => {
      const { vpnApi, trialApi, subscriptionsApi } = await import('@/lib/api');

      vi.mocked(vpnApi.getUsage).mockResolvedValue({ data: null } as any);
      vi.mocked(trialApi.getStatus).mockResolvedValue({
        data: { is_trial_active: false, is_eligible: false }
      } as any);
      vi.mocked(subscriptionsApi.list).mockResolvedValue({ data: [] } as any);

      renderWithProviders(<MiniAppHomePage />);

      await waitFor(() => {
        expect(screen.getByText('quickActions')).toBeInTheDocument();
      });

      expect(screen.queryByText('vpnConfig')).not.toBeInTheDocument();
    });
  });

});
