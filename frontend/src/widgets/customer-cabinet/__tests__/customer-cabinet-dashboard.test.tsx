import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  getBalanceMock,
  getCountersMock,
  getCurrentEntitlementMock,
  getCurrentServiceStateMock,
  getProfileMock,
  getReferralStatsMock,
  getTrialStatusMock,
  getUsageMock,
  listNotificationsMock,
} = vi.hoisted(() => ({
  getBalanceMock: vi.fn(),
  getCountersMock: vi.fn(),
  getCurrentEntitlementMock: vi.fn(),
  getCurrentServiceStateMock: vi.fn(),
  getProfileMock: vi.fn(),
  getReferralStatsMock: vi.fn(),
  getTrialStatusMock: vi.fn(),
  getUsageMock: vi.fn(),
  listNotificationsMock: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations:
    () =>
    (key: string, values?: Record<string, string | number>) => {
      if (!values) {
        return key;
      }

      return `${key} ${Object.values(values).join(' ')}`;
    },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('@/lib/api', () => ({
  entitlementsApi: {
    getCurrent: getCurrentEntitlementMock,
  },
  growthNotificationsApi: {
    getCounters: getCountersMock,
    list: listNotificationsMock,
  },
  profileApi: {
    getProfile: getProfileMock,
  },
  referralApi: {
    getStats: getReferralStatsMock,
  },
  serviceAccessApi: {
    getCurrentServiceState: getCurrentServiceStateMock,
  },
  trialApi: {
    getStatus: getTrialStatusMock,
  },
  vpnApi: {
    getUsage: getUsageMock,
  },
  walletApi: {
    getBalance: getBalanceMock,
  },
}));

import { CustomerCabinetDashboard } from '../customer-cabinet-dashboard';

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const activeEntitlement = {
  addons: [],
  display_name: 'Pro',
  effective_entitlements: {
    connection_modes: ['wireguard'],
    device_limit: 5,
    display_traffic_label: '2 TB',
    support_sla: 'priority',
  },
  expires_at: '2030-05-24T00:00:00Z',
  invite_bundle: {},
  is_trial: false,
  period_days: 30,
  plan_code: 'pro',
  plan_uuid: 'plan-1',
  status: 'active',
};

const activeServiceState = {
  access_delivery_channel: {
    channel_status: 'active',
    channel_type: 'shared_client',
  },
  consumption_context: {},
  device_credential: {
    credential_status: 'active',
  },
  provisioning_profile: {
    profile_key: 'default',
  },
  service_identity: {
    identity_status: 'active',
  },
};

const usageSnapshot = {
  bandwidth_limit_bytes: 100,
  bandwidth_used_bytes: 50,
  connections_active: 1,
  connections_limit: 5,
  generated_at: '2026-04-24T10:00:05Z',
  last_connection_at: '2026-04-24T10:00:00Z',
  period_end: '2030-05-24T00:00:00Z',
  period_start: '2026-04-24T00:00:00Z',
  usage_available: true,
  usage_source: 'remnawave',
  usage_unavailable_reason: null,
};

const rewardNotification = {
  action_required: false,
  created_at: '2026-04-24T11:00:00Z',
  id: 'notification-1',
  kind: 'reward',
  message: 'Referral reward is available.',
  notes: [],
  route_slug: 'referral',
  title: 'Reward ready',
  tone: 'positive',
  unread: true,
};

beforeEach(() => {
  vi.clearAllMocks();

  getCurrentEntitlementMock.mockResolvedValue({ data: activeEntitlement });
  getCountersMock.mockResolvedValue({
    data: {
      action_required_notifications: 0,
      total_notifications: 3,
      unread_notifications: 1,
    },
  });
  listNotificationsMock.mockResolvedValue({
    data: [rewardNotification],
  });
  getProfileMock.mockResolvedValue({
    data: {
      avatar_url: null,
      display_name: 'Alice',
      email: 'alice@example.com',
      id: 'user-1',
      language: 'en',
      timezone: 'UTC',
      updated_at: '2026-04-24T00:00:00Z',
    },
  });
  getReferralStatsMock.mockResolvedValue({
    data: {
      available_rewards_usd: 4,
      commission_rate: 10,
      lifetime_cap_used_usd: 0,
      monthly_cap_used_usd: 0,
      pending_rewards_usd: 2,
      qualifying_orders: 1,
      reversed_rewards_usd: 0,
      total_earned: 6,
      total_referrals: 2,
    },
  });
  getCurrentServiceStateMock.mockResolvedValue({ data: activeServiceState });
  getTrialStatusMock.mockResolvedValue({
    data: {
      days_remaining: 0,
      is_eligible: false,
      is_trial_active: false,
      trial_end: null,
      trial_start: null,
    },
  });
  getUsageMock.mockResolvedValue({ data: usageSnapshot });
  getBalanceMock.mockResolvedValue({
    data: {
      balance: 12.5,
      currency: 'USD',
      frozen: 1,
      id: 'wallet-1',
    },
  });
});

describe('CustomerCabinetDashboard', () => {
  it('renders backend-backed customer cabinet signals and safe actions', async () => {
    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Pro')).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-access')).getByText(
        'stage1States.access.active.title',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-payment')).getByText(
        'stage1States.payment.paid.title',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-provisioning')).getByText(
        'stage1States.provisioning.ready.title',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('50 B')).toBeInTheDocument();
    expect(screen.getByText('$12.50')).toBeInTheDocument();
    expect(screen.getByText('Shared Client')).toBeInTheDocument();
    expect(screen.getByText('default')).toBeInTheDocument();
    expect(await screen.findByText('Reward ready')).toBeInTheDocument();
    expect(screen.getByText('sync.title')).toBeInTheDocument();

    expect(
      screen.getByRole('link', { name: /actions\.managePlan/i }),
    ).toHaveAttribute('href', '/subscriptions');
    expect(
      screen.getAllByRole('link', { name: /actions\.getConfig/i })[0],
    ).toHaveAttribute('href', '/servers');
    expect(
      screen.getByRole('link', { name: /actions\.secureAccount/i }),
    ).toHaveAttribute('href', '/settings');
    expect(screen.queryByRole('link', { name: /actions\.invite/i })).not.toBeInTheDocument();
    expect(getReferralStatsMock).not.toHaveBeenCalled();
    expect(listNotificationsMock).toHaveBeenCalledWith(false);
  });

  it('renders S1 grace, payment pending, and provisioning retry states', async () => {
    getCurrentEntitlementMock.mockResolvedValueOnce({
      data: {
        ...activeEntitlement,
        effective_entitlements: {
          ...activeEntitlement.effective_entitlements,
          stage1_payment_state: 'pending',
          stage1_provisioning_state: 'retrying',
        },
        expires_at: '2026-04-23T00:00:00Z',
        status: 'grace_period',
      },
    });

    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('health.attention.title')).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-access')).getByText(
        'stage1States.access.grace.title',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-payment')).getByText(
        'stage1States.payment.pending.title',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-provisioning')).getByText(
        'stage1States.provisioning.retrying.title',
      ),
    ).toBeInTheDocument();
  });

  it('renders S1 expired access with failed payment and provisioning states', async () => {
    getCurrentEntitlementMock.mockResolvedValueOnce({
      data: {
        ...activeEntitlement,
        effective_entitlements: {
          stage1_payment_state: 'failed',
          stage1_provisioning_state: 'failed',
        },
        expires_at: '2026-04-01T00:00:00Z',
        status: 'expired',
      },
    });

    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('health.critical.title')).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-access')).getByText(
        'stage1States.access.expired.title',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-payment')).getByText(
        'stage1States.payment.failed.title',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('stage1-state-provisioning')).getByText(
        'stage1States.provisioning.failed.title',
      ),
    ).toBeInTheDocument();
  });

  it('surfaces degraded backend state and retries failed cabinet resources', async () => {
    getUsageMock
      .mockRejectedValueOnce(new Error('usage unavailable'))
      .mockResolvedValueOnce({ data: usageSnapshot });
    getCurrentServiceStateMock
      .mockRejectedValueOnce(new Error('service state unavailable'))
      .mockResolvedValueOnce({ data: activeServiceState });
    listNotificationsMock
      .mockRejectedValueOnce(new Error('notifications unavailable'))
      .mockResolvedValueOnce({ data: [rewardNotification] });

    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('sync.status.degraded')).toBeInTheDocument();
    expect(screen.getByText('sync.issues 3')).toBeInTheDocument();
    expect(screen.getByText('readiness.degraded')).toBeInTheDocument();
    expect(screen.getByText('notifications.errorTitle')).toBeInTheDocument();
    expect(screen.getByText('notifications.errorDescription')).toBeInTheDocument();

    const trafficCard = screen.getByText('metrics.traffic.title').closest('article');
    expect(trafficCard).not.toBeNull();
    fireEvent.click(within(trafficCard!).getByRole('button', { name: 'retry' }));

    await waitFor(() => {
      expect(getUsageMock).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText('50 B')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'sync.retryAll' }));

    await waitFor(() => {
      expect(getCurrentServiceStateMock).toHaveBeenCalledTimes(2);
      expect(listNotificationsMock).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText('Shared Client')).toBeInTheDocument();
    expect(screen.getByText('Reward ready')).toBeInTheDocument();
  });

  it('prioritizes critical trial, provisioning, traffic and alert actions', async () => {
    getCurrentEntitlementMock.mockResolvedValueOnce({
      data: {
        ...activeEntitlement,
        display_name: null,
        effective_entitlements: {},
        expires_at: '2026-04-01T00:00:00Z',
        plan_code: null,
        status: 'expired',
      },
    });
    getCountersMock.mockResolvedValueOnce({
      data: {
        action_required_notifications: 2,
        total_notifications: 4,
        unread_notifications: 3,
      },
    });
    listNotificationsMock.mockResolvedValueOnce({ data: [] });
    getCurrentServiceStateMock.mockResolvedValueOnce({
      data: {
        access_delivery_channel: null,
        consumption_context: {},
        device_credential: null,
        provisioning_profile: null,
        service_identity: {
          identity_status: '',
        },
      },
    });
    getTrialStatusMock.mockResolvedValueOnce({
      data: {
        days_remaining: 2,
        is_eligible: true,
        is_trial_active: true,
        trial_end: '2026-04-26T00:00:00Z',
        trial_start: '2026-04-24T00:00:00Z',
      },
    });
    getUsageMock.mockResolvedValueOnce({
      data: {
        ...usageSnapshot,
        bandwidth_used_bytes: 98,
        last_connection_at: null,
      },
    });

    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('health.critical.title')).toBeInTheDocument();
    expect(screen.getByText('health.critical.description')).toBeInTheDocument();
    expect(screen.getByText('noActivePlan')).toBeInTheDocument();
    expect(screen.getByText('readiness.noConnectionYet')).toBeInTheDocument();
    expect(screen.getByText('notifications.empty')).toBeInTheDocument();
    expect(screen.getByText('plan.trialActive 2')).toBeInTheDocument();

    expect(
      screen.getByRole('link', { name: /actions\.startTrial/i }),
    ).toHaveAttribute('href', '/subscriptions');
    expect(
      screen.getAllByRole('link', { name: /actions\.finishProvisioning/i })[0],
    ).toHaveAttribute('href', '/servers');
    expect(
      screen.getByRole('link', { name: /actions\.watchTraffic/i }),
    ).toHaveAttribute('href', '#cabinet-usage');
    expect(
      screen.getByRole('link', { name: /actions\.reviewNotifications/i }),
    ).toHaveAttribute('href', '#cabinet-notifications');
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '98');
  });

  it('uses safe fallbacks for anonymous profile, unmetered usage and missing service data', async () => {
    getProfileMock.mockResolvedValueOnce({
      data: {
        avatar_url: null,
        display_name: '',
        email: '',
        id: 'user-1',
        language: 'en',
        timezone: 'UTC',
        updated_at: '2026-04-24T00:00:00Z',
      },
    });
    getCurrentEntitlementMock.mockResolvedValueOnce({
      data: {
        ...activeEntitlement,
        display_name: null,
        effective_entitlements: {},
        expires_at: null,
        plan_code: null,
      },
    });
    getCurrentServiceStateMock.mockResolvedValueOnce({
      data: {
        access_delivery_channel: null,
        consumption_context: {},
        device_credential: null,
        provisioning_profile: null,
        service_identity: null,
      },
    });
    getUsageMock.mockResolvedValueOnce({
      data: {
        ...usageSnapshot,
        bandwidth_limit_bytes: 0,
        bandwidth_used_bytes: 0,
        last_connection_at: null,
        period_end: null,
        usage_available: false,
        usage_source: 'unavailable',
        usage_unavailable_reason: 'upstream_user_not_found',
      },
    });

    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('anonymousUser')).toBeInTheDocument();
    expect(screen.getByText('noActivePlan')).toBeInTheDocument();
    expect(screen.getAllByText('unknownDate')).not.toHaveLength(0);
    expect(screen.getAllByText('pendingProvisioning')).not.toHaveLength(0);
    expect(screen.getByText('plan.defaultSecurity')).toBeInTheDocument();
    expect(screen.getByText('plan.standardSupport')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText('metricUnavailable')).not.toHaveLength(0);
    });
    expect(screen.getAllByText('unlimited')).not.toHaveLength(0);
  });

  it('retries degraded metric cards and refreshes the notification panel', async () => {
    getUsageMock
      .mockRejectedValueOnce(new Error('usage unavailable'))
      .mockRejectedValueOnce(new Error('usage still unavailable'))
      .mockResolvedValueOnce({ data: usageSnapshot });
    getBalanceMock
      .mockRejectedValueOnce(new Error('wallet unavailable'))
      .mockResolvedValueOnce({
        data: {
          balance: 12.5,
          currency: 'USD',
          frozen: 1,
          id: 'wallet-1',
        },
      });
    getCountersMock
      .mockRejectedValueOnce(new Error('counters unavailable'))
      .mockResolvedValueOnce({
        data: {
          action_required_notifications: 1,
          total_notifications: 3,
          unread_notifications: 1,
        },
      });
    getReferralStatsMock
      .mockRejectedValueOnce(new Error('referral unavailable'))
      .mockRejectedValueOnce(new Error('referral still unavailable'))
      .mockRejectedValueOnce(new Error('referral final retry unavailable'))
      .mockResolvedValueOnce({
        data: {
          available_rewards_usd: 4,
          commission_rate: 10,
          lifetime_cap_used_usd: 0,
          monthly_cap_used_usd: 0,
          pending_rewards_usd: 2,
          qualifying_orders: 1,
          reversed_rewards_usd: 0,
          total_earned: 6,
          total_referrals: 2,
        },
      });
    getCurrentServiceStateMock
      .mockRejectedValueOnce(new Error('service state unavailable'))
      .mockResolvedValueOnce({ data: activeServiceState });
    const actionRequiredNotification = {
      ...rewardNotification,
      action_required: true,
      id: 'notification-action-required',
      title: 'Payment review needed',
      unread: false,
    };
    listNotificationsMock
      .mockResolvedValueOnce({ data: [actionRequiredNotification] })
      .mockResolvedValueOnce({ data: [actionRequiredNotification] });

    renderWithQueryClient(<CustomerCabinetDashboard />);

    expect(await screen.findByText('sync.status.degraded')).toBeInTheDocument();

    const trafficCard = screen.getByText('metrics.traffic.title').closest('article');
    expect(trafficCard).not.toBeNull();
    fireEvent.click(within(trafficCard!).getByRole('button', { name: 'retry' }));

    await waitFor(() => {
      expect(getUsageMock).toHaveBeenCalledTimes(2);
    });

    const deviceCard = screen.getByText('metrics.devices.title').closest('article');
    expect(deviceCard).not.toBeNull();
    fireEvent.click(within(deviceCard!).getByRole('button', { name: 'retry' }));

    await waitFor(() => {
      expect(getUsageMock).toHaveBeenCalledTimes(3);
    });

    const walletCard = screen.getByText('metrics.wallet.title').closest('article');
    expect(walletCard).not.toBeNull();
    fireEvent.click(within(walletCard!).getByRole('button', { name: 'retry' }));

    const inboxCard = screen.getByText('metrics.notifications.title').closest('article');
    expect(inboxCard).not.toBeNull();
    fireEvent.click(within(inboxCard!).getByRole('button', { name: 'retry' }));

    expect(screen.queryByText('rewards.referrals')).not.toBeInTheDocument();

    const readinessPanel = screen.getByText('readiness.title').closest('article');
    expect(readinessPanel).not.toBeNull();
    fireEvent.click(within(readinessPanel!).getByRole('button', { name: 'retry' }));

    fireEvent.click(
      screen.getByRole('button', { name: 'notifications.refresh' }),
    );

    await waitFor(() => {
      expect(getBalanceMock).toHaveBeenCalledTimes(2);
      expect(getCountersMock).toHaveBeenCalledTimes(2);
      expect(getCurrentServiceStateMock).toHaveBeenCalledTimes(2);
      expect(getReferralStatsMock).not.toHaveBeenCalled();
      expect(listNotificationsMock).toHaveBeenCalledTimes(2);
    });
    expect(screen.getByText('notifications.actionRequired')).toBeInTheDocument();
    expect(screen.getByText('Payment review needed')).toBeInTheDocument();
  });
});
