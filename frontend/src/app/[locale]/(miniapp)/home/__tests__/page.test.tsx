/**
 * Mini App Home Page Tests
 *
 * Tests the home/dashboard page for Telegram Mini App:
 * - Subscription status card (active/trial/none)
 * - Usage stats display
 * - Trial eligibility and activation link
 * - Quick actions grid
 * - VPN config card integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HomePage from '../page';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock next/navigation
vi.mock('@/i18n/navigation', () => ({
  Link: ({ href, onClick, children, className }: any) => (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  ),
}));

// Mock VpnConfigCard to simplify testing
vi.mock('../../components/VpnConfigCard', () => ({
  VpnConfigCard: ({ colorScheme }: any) => (
    <div data-testid="vpn-config-card" data-colorscheme={colorScheme}>
      VPN Config Card
    </div>
  ),
}));

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockUsageData = {
  bandwidth_used_bytes: 5368709120, // 5 GB
  bandwidth_limit_bytes: 107374182400, // 100 GB
  connections_active: 2,
  connections_limit: 5,
  last_connection_at: '2026-02-11T10:00:00Z',
};

const mockTrialData = {
  is_trial_active: false,
  is_eligible: true,
  trial_end: null,
  days_remaining: 0,
};

describe('MiniAppHomePage', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  describe('Loading State', () => {
    it('test_shows_loading_spinner_while_fetching_data', () => {
      server.use(
        http.get(`${API_BASE}/usage`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(mockTrialData);
        })
      );

      render(<HomePage />, { wrapper: createWrapper() });

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
    });
  });

  describe('Subscription Status Card - No Subscription', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_displays_no_subscription_message', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      expect(screen.getByText('noSubscriptionDescription')).toBeInTheDocument();
    });

    it('test_does_not_show_trial_badge_when_not_on_trial', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      expect(screen.queryByText('trial')).not.toBeInTheDocument();
    });

    it('test_does_not_show_usage_stats_without_subscription', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      expect(screen.queryByText('usage')).not.toBeInTheDocument();
      expect(screen.queryByText('dataUsed')).not.toBeInTheDocument();
    });
  });

  describe('Subscription Status Card - On Trial', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: true,
            is_eligible: false,
            trial_end: '2026-02-18T23:59:59Z',
            days_remaining: 7,
          });
        })
      );
    });

    it('test_displays_subscription_active_when_on_trial', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('subscriptionActive')).toBeInTheDocument();
      });
    });

    it('test_shows_trial_badge', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('trial')).toBeInTheDocument();
      });
    });

    it('test_displays_trial_plan_info', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('plan:')).toBeInTheDocument();
      });

      expect(screen.getByText('trialPlan')).toBeInTheDocument();
    });

    it('test_displays_trial_expiry_date', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('expires:')).toBeInTheDocument();
      });

      expect(screen.getByText(/2\/18\/2026/)).toBeInTheDocument();
    });

    it('test_displays_days_remaining', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('daysRemaining:')).toBeInTheDocument();
      });

      expect(screen.getByText('7')).toBeInTheDocument();
    });

    it('test_shows_usage_stats_when_on_trial', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('usage')).toBeInTheDocument();
      });

      expect(screen.getByText('dataUsed')).toBeInTheDocument();
    });
  });

  describe('Usage Stats Display', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: true,
            is_eligible: false,
            trial_end: '2026-02-18T23:59:59Z',
            days_remaining: 7,
          });
        })
      );
    });

    it('test_displays_data_usage_with_formatted_bytes', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('dataUsed')).toBeInTheDocument();
      });

      // 5 GB / 100 GB
      expect(screen.getByText(/5\.00 GB/)).toBeInTheDocument();
      expect(screen.getByText(/100\.00 GB/)).toBeInTheDocument();
    });

    it('test_displays_usage_percentage_progress_bar', async () => {
      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('dataUsed')).toBeInTheDocument();
      });

      // Progress bar should exist
      const progressBar = container.querySelector('.h-2.bg-muted');
      expect(progressBar).toBeInTheDocument();
    });

    it('test_displays_active_connections_count', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('connections')).toBeInTheDocument();
      });

      expect(screen.getByText('2 / 5')).toBeInTheDocument();
    });

    it('test_displays_last_connection_time', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('lastConnected')).toBeInTheDocument();
      });

      // Date formatting varies by locale, just check it exists
      const lastConnectionText = screen.getByText(/2\/11\/2026/);
      expect(lastConnectionText).toBeInTheDocument();
    });

    it('test_shows_red_progress_bar_when_usage_over_80_percent', async () => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json({
            ...mockUsageData,
            bandwidth_used_bytes: 85899345920, // 80 GB (80%)
          });
        })
      );

      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('dataUsed')).toBeInTheDocument();
      });

      // Should show destructive color for high usage
      const progressBarFill = container.querySelector('.bg-destructive');
      expect(progressBarFill).toBeInTheDocument();
    });

    it('test_shows_cyan_progress_bar_when_usage_under_80_percent', async () => {
      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('dataUsed')).toBeInTheDocument();
      });

      // Should show cyan color for normal usage
      const progressBarFill = container.querySelector('.bg-neon-cyan');
      expect(progressBarFill).toBeInTheDocument();
    });
  });

  describe('Trial Eligibility Section', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: false,
            is_eligible: true,
            trial_end: null,
            days_remaining: 0,
          });
        })
      );
    });

    it('test_shows_trial_available_card_when_eligible', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('trialAvailable')).toBeInTheDocument();
      });

      expect(screen.getByText('trialDescription')).toBeInTheDocument();
    });

    it('test_shows_activate_trial_link', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });

      const link = screen.getByText('activateTrial').closest('a');
      expect(link).toHaveAttribute('href', '/plans');
    });

    it('test_triggers_haptic_feedback_on_activate_trial_click', async () => {
      const user = userEvent.setup();

      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('activateTrial')).toBeInTheDocument();
      });

      const link = screen.getByText('activateTrial');
      await user.click(link);

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('medium');
    });

    it('test_hides_trial_section_when_not_eligible', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: false,
            is_eligible: false,
            trial_end: null,
            days_remaining: 0,
          });
        })
      );

      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      expect(screen.queryByText('trialAvailable')).not.toBeInTheDocument();
    });
  });

  describe('VPN Config Card', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_renders_vpn_config_card', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('vpn-config-card')).toBeInTheDocument();
      });
    });

    it('test_passes_color_scheme_to_vpn_config_card', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        const configCard = screen.getByTestId('vpn-config-card');
        expect(configCard).toHaveAttribute('data-colorscheme', 'dark');
      });
    });
  });

  describe('Quick Actions Grid', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );
    });

    it('test_displays_quick_actions_title', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('quickActions')).toBeInTheDocument();
      });
    });

    it('test_displays_view_plans_action', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('viewPlans')).toBeInTheDocument();
      });

      const link = screen.getByText('viewPlans').closest('a');
      expect(link).toHaveAttribute('href', '/plans');
    });

    it('test_displays_wallet_action', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('wallet')).toBeInTheDocument();
      });

      const link = screen.getByText('wallet').closest('a');
      expect(link).toHaveAttribute('href', '/wallet');
    });

    it('test_displays_settings_action', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('settings')).toBeInTheDocument();
      });

      const link = screen.getByText('settings').closest('a');
      expect(link).toHaveAttribute('href', '/profile');
    });

    it('test_shows_vpn_config_action_when_on_trial', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_trial_active: true,
            is_eligible: false,
            trial_end: '2026-02-18T23:59:59Z',
            days_remaining: 7,
          });
        })
      );

      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('vpnConfig')).toBeInTheDocument();
      });

      const link = screen.getByText('vpnConfig').closest('a');
      expect(link).toHaveAttribute('href', '/profile#vpn-config');
    });

    it('test_hides_vpn_config_action_without_subscription', async () => {
      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('quickActions')).toBeInTheDocument();
      });

      expect(screen.queryByText('vpnConfig')).not.toBeInTheDocument();
    });

    it('test_triggers_haptic_on_quick_action_click', async () => {
      const user = userEvent.setup();

      render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('viewPlans')).toBeInTheDocument();
      });

      const plansLink = screen.getByText('viewPlans');
      await user.click(plansLink);

      expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('medium');
    });
  });

  describe('Theme Integration', () => {
    it('test_uses_dark_theme_by_default', async () => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );

      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      // Should use dark theme classes
      const cards = container.querySelectorAll('[class*="bg-[var(--tg-bg-color"]');
      expect(cards.length).toBeGreaterThan(0);
    });

    it('test_uses_light_theme_when_telegram_in_light_mode', async () => {
      cleanupTelegramWebAppMock();
      setupTelegramWebAppMock({ colorScheme: 'light' });

      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );

      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('noSubscription')).toBeInTheDocument();
      });

      // Color scheme should be light
      expect(container.querySelector('[class*="bg-[var(--tg-bg-color"]')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('test_handles_usage_api_error_gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(mockTrialData);
        })
      );

      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(container.querySelector('.animate-spin')).not.toBeInTheDocument();
      });

      // Should still render page without usage stats
      expect(screen.getByText('noSubscription')).toBeInTheDocument();
    });

    it('test_handles_trial_api_error_gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/usage`, () => {
          return HttpResponse.json(mockUsageData);
        }),
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      const { container } = render(<HomePage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(container.querySelector('.animate-spin')).not.toBeInTheDocument();
      });

      // Should still render page
      expect(screen.queryByText('quickActions')).toBeInTheDocument();
    });
  });
});
