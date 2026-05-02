import type React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MiniAppHomePage from '../../page';
import {
  cleanupTelegramWebAppMock,
  setupTelegramWebAppMock,
} from '@/test/mocks/telegram-webapp';

const { mockGetBootstrap, mockEmitMiniAppRuntimeEvent } = vi.hoisted(() => ({
  mockGetBootstrap: vi.fn(),
  mockEmitMiniAppRuntimeEvent: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  miniappApi: {
    getBootstrap: mockGetBootstrap,
  },
}));

vi.mock('@/features/miniapp-runtime/lib/runtime-analytics', () => ({
  emitMiniAppRuntimeEvent: mockEmitMiniAppRuntimeEvent,
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({ children, href, ...props }: React.ComponentProps<'a'>) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('../../components/VpnConfigCard', () => ({
  VpnConfigCard: () => <div data-testid="vpn-config-card">VPN Config Card</div>,
}));

const baseBootstrap = {
  session: {
    authenticated: true,
    userId: 'user-001',
    telegramUserId: '123456789',
    authRealm: 'customer',
  },
  runtime: {
    surface: 'telegram_miniapp',
    tenant: {
      kind: 'platform',
      partnerId: null,
      workspaceId: null,
      storefrontId: null,
      botId: null,
    },
    brand: {
      name: 'CyberVPN',
      logoUrl: null,
      primaryColor: '#00ffff',
      supportUrl: null,
      legalName: null,
    },
    commercialPolicy: {
      pricingPolicyId: 'default',
      currencyPolicy: 'USD',
      revenueSharePolicyId: null,
      trialPolicyId: 'trial-default',
    },
    attribution: {
      source: 'telegram',
      surface: 'miniapp',
      referralCode: null,
      campaign: null,
      startParam: null,
    },
  },
  user: {
    firstName: 'Test',
    username: 'testuser',
    photoUrl: null,
    locale: 'en-EN',
    rtl: false,
  },
  subscription: {
    status: 'none',
    planId: null,
    planName: null,
    expiresAt: null,
    autoRenew: false,
  },
  trial: {
    eligible: false,
    reason: null,
    durationDays: 7,
    trialStart: null,
    trialEnd: null,
    daysRemaining: 0,
  },
  wallet: {
    balance: 0,
    currency: 'USD',
    bonusesAvailable: 0,
  },
  devices: {
    activeCount: 0,
    limit: 5,
    hasConfig: false,
  },
  usage: {
    bandwidthUsedBytes: 0,
    bandwidthLimitBytes: 0,
    connectionsActive: 0,
    connectionsLimit: 5,
    periodStart: null,
    periodEnd: null,
    lastConnectionAt: null,
  },
  serviceState: {
    providerName: null,
    channelType: null,
  },
  recommendedServer: null,
  primaryCta: {
    kind: 'buy_plan',
    label: 'Choose plan',
  },
  referral: {
    code: null,
    inviteUrl: null,
    shareText: null,
  },
  payment: {
    unresolvedPaymentId: null,
    lastStatus: null,
  },
  support: {
    url: null,
    paysupportCommandAvailable: false,
  },
  rollout: {
    enabled: true,
    mode: 'live',
    trialEnabled: true,
    checkoutEnabled: true,
    configEnabled: true,
    accessGranted: true,
    isCanaryUser: false,
    gateReasonCode: null,
    maintenanceMessage: null,
  },
  featureFlags: {},
  freshness: {
    generatedAt: '2026-04-24T00:00:00Z',
  },
};

function bootstrap(overrides: Record<string, unknown> = {}) {
  return {
    ...baseBootstrap,
    ...overrides,
    session: { ...baseBootstrap.session, ...(overrides.session as object | undefined) },
    runtime: { ...baseBootstrap.runtime, ...(overrides.runtime as object | undefined) },
    user: { ...baseBootstrap.user, ...(overrides.user as object | undefined) },
    subscription: {
      ...baseBootstrap.subscription,
      ...(overrides.subscription as object | undefined),
    },
    trial: { ...baseBootstrap.trial, ...(overrides.trial as object | undefined) },
    wallet: { ...baseBootstrap.wallet, ...(overrides.wallet as object | undefined) },
    devices: { ...baseBootstrap.devices, ...(overrides.devices as object | undefined) },
    usage: { ...baseBootstrap.usage, ...(overrides.usage as object | undefined) },
    serviceState: {
      ...baseBootstrap.serviceState,
      ...(overrides.serviceState as object | undefined),
    },
    primaryCta: {
      ...baseBootstrap.primaryCta,
      ...(overrides.primaryCta as object | undefined),
    },
    rollout: { ...baseBootstrap.rollout, ...(overrides.rollout as object | undefined) },
  };
}

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
    </QueryClientProvider>,
  );
}

describe('MiniApp Home Page', () => {
  beforeEach(() => {
    setupTelegramWebAppMock();
    mockGetBootstrap.mockResolvedValue({ data: bootstrap() });
    mockEmitMiniAppRuntimeEvent.mockResolvedValue(undefined);
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  it('test_displays_loading_spinner', () => {
    mockGetBootstrap.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<MiniAppHomePage />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('test_displays_no_subscription_message_without_usage_stats', async () => {
    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('noSubscription')).toBeInTheDocument();
    });

    expect(screen.queryByText('usage')).not.toBeInTheDocument();
    expect(screen.queryByText('vpnConfig')).not.toBeInTheDocument();
  });

  it('test_displays_active_subscription_summary', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({
        subscription: {
          status: 'active',
          planId: 'plan-pro-001',
          planName: 'Premium',
          expiresAt: '2026-12-31T23:59:59Z',
          autoRenew: true,
        },
        serviceState: {
          providerName: 'remnawave',
          channelType: 'telegram_bot',
        },
        devices: {
          activeCount: 1,
          limit: 10,
          hasConfig: true,
        },
      }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('subscriptionActive')).toBeInTheDocument();
      expect(screen.getByText('Premium')).toBeInTheDocument();
      expect(screen.getByText('remnawave')).toBeInTheDocument();
    });
  });

  it('test_displays_trial_badge_and_trial_usage', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({
        subscription: { status: 'trial' },
        trial: {
          eligible: false,
          trialEnd: '2026-05-01T23:59:59Z',
          daysRemaining: 7,
        },
        usage: {
          bandwidthUsedBytes: 2 * 1024 ** 3,
          bandwidthLimitBytes: 10 * 1024 ** 3,
          connectionsActive: 3,
          connectionsLimit: 5,
          lastConnectionAt: '2026-04-24T10:00:00Z',
        },
      }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('trial')).toBeInTheDocument();
      expect(screen.getByText('usage')).toBeInTheDocument();
      expect(screen.getByText(/2\.00 GB \/ 10\.00 GB/)).toBeInTheDocument();
      expect(screen.getByText('3 / 5')).toBeInTheDocument();
    });
  });

  it('test_uses_cyan_progress_bar_under_80_percent', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({
        subscription: { status: 'active' },
        usage: {
          bandwidthUsedBytes: 5 * 1024 ** 3,
          bandwidthLimitBytes: 10 * 1024 ** 3,
          connectionsActive: 1,
          connectionsLimit: 5,
        },
      }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(document.querySelector('.bg-neon-cyan')).toBeInTheDocument();
    });
  });

  it('test_uses_red_progress_bar_at_80_percent_or_more', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({
        subscription: { status: 'active' },
        usage: {
          bandwidthUsedBytes: 9 * 1024 ** 3,
          bandwidthLimitBytes: 10 * 1024 ** 3,
          connectionsActive: 1,
          connectionsLimit: 5,
        },
      }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(document.querySelector('.bg-destructive')).toBeInTheDocument();
    });
  });

  it('test_shows_trial_available_card_when_rollout_allows_trial', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({
        trial: {
          eligible: true,
          durationDays: 7,
          daysRemaining: 0,
        },
      }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('trialAvailable')).toBeInTheDocument();
      expect(screen.getByText('activateTrial')).toBeInTheDocument();
    });
  });

  it('test_hides_trial_card_when_rollout_disables_trial', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({
        trial: { eligible: true },
        rollout: { trialEnabled: false },
      }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('noSubscription')).toBeInTheDocument();
    });

    expect(screen.queryByText('trialAvailable')).not.toBeInTheDocument();
  });

  it('test_displays_quick_actions', async () => {
    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('quickActions')).toBeInTheDocument();
      expect(screen.getByText('viewPlans')).toBeInTheDocument();
      expect(screen.getByText('wallet')).toBeInTheDocument();
      expect(screen.getByText('settings')).toBeInTheDocument();
    });
  });

  it('test_vpn_config_action_is_shown_only_with_subscription_or_trial', async () => {
    mockGetBootstrap.mockResolvedValue({
      data: bootstrap({ subscription: { status: 'active' } }),
    });

    renderWithProviders(<MiniAppHomePage />);

    await waitFor(() => {
      expect(screen.getByText('vpnConfig')).toBeInTheDocument();
    });
  });
});
