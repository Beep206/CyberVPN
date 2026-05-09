import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import HomePage from '../page';
import { server } from '@/test/mocks/server';
import { cleanupTelegramWebAppMock, setupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({ href, onClick, children, className }: React.ComponentProps<'a'>) => (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  ),
}));

vi.mock('@/features/miniapp-runtime/lib/runtime-analytics', () => ({
  emitMiniAppRuntimeEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../../components/VpnConfigCard', () => ({
  VpnConfigCard: ({ colorScheme }: { colorScheme?: string }) => (
    <div data-testid="vpn-config-card" data-colorscheme={colorScheme}>
      VPN Config Card
    </div>
  ),
}));

const API_BASE = '*/api/v1';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createBootstrap(overrides: Record<string, unknown> = {}) {
  return {
    session: {
      authenticated: true,
      userId: 'user-1',
      telegramUserId: '123456789',
      authRealm: 'customer',
    },
    runtime: {
      surface: 'telegram_miniapp',
      tenant: { kind: 'platform' },
      brand: {
        name: 'CyberVPN',
        primaryColor: '#00ffff',
        supportUrl: 'https://t.me/cybervpn_bot?start=support',
        legalName: 'CyberVPN',
      },
      commercialPolicy: {
        pricingPolicyId: 'cybervpn-miniapp-default',
        currencyPolicy: 'telegram_stars_xtr',
        trialPolicyId: 'cybervpn-default-trial',
      },
      attribution: {
        source: 'telegram',
        surface: 'miniapp',
      },
    },
    user: {
      firstName: 'cyber',
      username: 'cyber',
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
      eligible: true,
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
      limit: 0,
      hasConfig: false,
    },
    usage: {
      bandwidthUsedBytes: 5368709120,
      bandwidthLimitBytes: 107374182400,
      connectionsActive: 2,
      connectionsLimit: 5,
      periodStart: '2026-02-01T00:00:00Z',
      periodEnd: '2026-03-01T00:00:00Z',
      lastConnectionAt: '2026-02-11T10:00:00Z',
      usageAvailable: true,
      usageSource: 'remnawave',
      usageUnavailableReason: null,
    },
    serviceState: {
      providerName: null,
      channelType: null,
    },
    recommendedServer: null,
    primaryCta: {
      kind: 'start_trial',
      label: 'Start trial',
    },
    referral: {
      code: 'REF12345',
      inviteUrl: 'https://t.me/cybervpn_bot?startapp=ref_REF12345',
      shareText: 'Try CyberVPN',
    },
    payment: {
      unresolvedPaymentId: null,
      lastStatus: null,
    },
    support: {
      url: 'https://t.me/cybervpn_bot?start=support',
      paysupportCommandAvailable: true,
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
    featureFlags: {
      miniapp_bootstrap_v1: true,
    },
    freshness: {
      generatedAt: '2026-04-22T12:00:00Z',
    },
    ...overrides,
  };
}

describe('MiniAppHomePage', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;
  let currentBootstrap: ReturnType<typeof createBootstrap>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
    currentBootstrap = createBootstrap();
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(currentBootstrap)),
    );
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  it('shows loading spinner while bootstrap is pending', () => {
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json(currentBootstrap);
      }),
    );

    render(<HomePage />, { wrapper: createWrapper() });

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders no-subscription state from bootstrap', async () => {
    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('noSubscription')).toBeInTheDocument();
    });

    expect(screen.getByText('noSubscriptionDescription')).toBeInTheDocument();
    expect(screen.getByText('trialAvailable')).toBeInTheDocument();
  });

  it('renders active subscription, provider, channel, and usage stats', async () => {
    currentBootstrap = createBootstrap({
      subscription: {
        status: 'active',
        planId: 'plan-pro',
        planName: 'Pro',
        expiresAt: '2026-06-01T00:00:00Z',
        autoRenew: false,
      },
      trial: {
        eligible: false,
        reason: 'already_used',
        durationDays: 7,
        trialStart: null,
        trialEnd: null,
        daysRemaining: 0,
      },
      devices: {
        activeCount: 1,
        limit: 5,
        hasConfig: true,
      },
      serviceState: {
        providerName: 'remnawave',
        channelType: 'telegram_bot',
      },
      primaryCta: {
        kind: 'select_server',
        label: 'Select server',
      },
    });
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(currentBootstrap)),
    );

    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('subscriptionActive')).toBeInTheDocument();
    });

    expect(screen.getByText('Pro')).toBeInTheDocument();
    expect(screen.getByText('remnawave')).toBeInTheDocument();
    expect(screen.getByText('telegram_bot')).toBeInTheDocument();
    expect(screen.getByText('usage')).toBeInTheDocument();
    expect(screen.getByText(/5\.00 GB/)).toBeInTheDocument();
    expect(screen.getByText('2 / 5')).toBeInTheDocument();
  });

  it('renders trial state from bootstrap', async () => {
    currentBootstrap = createBootstrap({
      subscription: {
        status: 'trial',
        planId: null,
        planName: null,
        expiresAt: null,
        autoRenew: false,
      },
      trial: {
        eligible: false,
        reason: 'already_used',
        durationDays: 7,
        trialStart: '2026-02-11T00:00:00Z',
        trialEnd: '2026-02-18T23:59:59Z',
        daysRemaining: 7,
      },
      devices: {
        activeCount: 1,
        limit: 1,
        hasConfig: true,
      },
      primaryCta: {
        kind: 'get_config',
        label: 'Get config',
      },
    });
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(currentBootstrap)),
    );

    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('trial')).toBeInTheDocument();
    });

    expect(screen.getByText('trialPlan')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('renders quick actions with miniapp-safe links', async () => {
    currentBootstrap = createBootstrap({
      subscription: {
        status: 'active',
        planId: 'plan-pro',
        planName: 'Pro',
        expiresAt: '2026-06-01T00:00:00Z',
        autoRenew: false,
      },
      trial: {
        eligible: false,
        reason: 'already_used',
        durationDays: 7,
        trialStart: null,
        trialEnd: null,
        daysRemaining: 0,
      },
      devices: {
        activeCount: 1,
        limit: 5,
        hasConfig: true,
      },
      primaryCta: {
        kind: 'select_server',
        label: 'Select server',
      },
    });
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(currentBootstrap)),
    );

    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('subscriptionActive')).toBeInTheDocument();
    });

    expect(screen.getByText('viewPlans').closest('a')).toHaveAttribute('href', '/miniapp/plans');
    expect(screen.getByText('wallet').closest('a')).toHaveAttribute('href', '/miniapp/wallet');
    expect(screen.getByText('settings').closest('a')).toHaveAttribute('href', '/miniapp/profile');
    expect(screen.getByText('vpnConfig').closest('a')).toHaveAttribute('href', '/miniapp/profile#vpn-config');
  });

  it('triggers haptic feedback when tapping quick actions', async () => {
    const user = userEvent.setup();
    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    await user.click(screen.getByText('viewPlans'));
    expect(telegramMock.HapticFeedback.impactOccurred).toHaveBeenCalledWith('medium');
  });

  it('passes telegram color scheme through to config card', async () => {
    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('vpn-config-card')).toHaveAttribute('data-colorscheme', 'dark');
    });
  });

  it('renders maintenance banner from rollout policy', async () => {
    currentBootstrap = createBootstrap({
      rollout: {
        enabled: false,
        mode: 'maintenance',
        trialEnabled: false,
        checkoutEnabled: false,
        configEnabled: false,
        accessGranted: false,
        isCanaryUser: false,
        gateReasonCode: 'maintenance',
        maintenanceMessage: 'Mini App maintenance window',
      },
    });
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(currentBootstrap)),
    );

    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('serviceMaintenanceTitle')).toBeInTheDocument();
    });

    expect(screen.getByText('Mini App maintenance window')).toBeInTheDocument();
  });

  it('renders limited rollout banner for canary-restricted users', async () => {
    currentBootstrap = createBootstrap({
      rollout: {
        enabled: true,
        mode: 'canary',
        trialEnabled: true,
        checkoutEnabled: true,
        configEnabled: true,
        accessGranted: false,
        isCanaryUser: false,
        gateReasonCode: 'canary_not_allowed',
        maintenanceMessage: null,
      },
    });
    server.use(
      http.get(`${API_BASE}/miniapp/bootstrap`, () => HttpResponse.json(currentBootstrap)),
    );

    render(<HomePage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('serviceMaintenanceTitle')).toBeInTheDocument();
    });

    expect(screen.getByText('limitedRolloutDescription')).toBeInTheDocument();
  });
});
