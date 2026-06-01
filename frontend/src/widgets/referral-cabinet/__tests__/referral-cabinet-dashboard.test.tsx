import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  clientCapabilitiesMock,
  copyMock,
  giftPurchaseMock,
  markPerformanceMock,
  queryFixtures,
  redeemGrowthCodeMock,
  refetchMock,
} = vi.hoisted(() => ({
  clientCapabilitiesMock: {
    data: {
      growth: {
        checkout_code_discounts: false,
        gift_codes: false,
        growth_hub: true,
        invites: false,
        promo_codes: false,
        referral: true,
      },
    },
  },
  copyMock: vi.fn(),
  giftPurchaseMock: vi.fn(),
  markPerformanceMock: vi.fn(),
  queryFixtures: {
    '["growth","notifications","counters"]': {
      action_required_notifications: 1,
      total_notifications: 1,
      unread_notifications: 1,
    },
    '["growth","notifications","referral-cabinet"]': [
      {
        action_required: true,
        archived_at: null,
        created_at: '2026-04-24T10:00:00Z',
        id: 'notification-1',
        kind: 'referral_reward_pending',
        message: 'Reward is on hold',
        notes: [],
        route_slug: 'referral',
        source_id: 'reward-1',
        source_kind: 'referral',
        title: 'Reward pending',
        tone: 'warning',
        unread: true,
      },
    ],
    '["growth","referral","code"]': { referral_code: 'CYBER42' },
    '["growth","referral","commissions"]': [
      {
        available_at: null,
        base_amount: 50,
        commission_amount: 5,
        commission_rate: 0.1,
        created_at: '2026-04-23T10:00:00Z',
        currency: 'USD',
        hold_until: '2026-04-30T10:00:00Z',
        id: 'commission-pending',
        referred_user_id: 'user-3',
        reversed_at: null,
        reward_status: 'pending',
        source_model: 'legacy_commission',
      },
    ],
    '["growth","referral","rewards"]': [
      {
        available_at: '2026-04-25T10:00:00Z',
        created_at: '2026-04-24T10:00:00Z',
        currency: 'USD',
        hold_until: null,
        id: 'reward-available',
        payment_id: 'payment-1',
        referred_user_id: 'user-2',
        reversed_at: null,
        reward_amount: 12,
        reward_status: 'available',
      },
    ],
    '["growth","referral","stats"]': {
      available_rewards_usd: 12,
      commission_rate: 0.1,
      lifetime_cap_used_usd: 100,
      monthly_cap_used_usd: 25,
      pending_rewards_usd: 5,
      qualifying_orders: 3,
      reversed_rewards_usd: 0,
      total_earned: 17,
      total_referrals: 4,
    },
    '["growth","referral","status"]': {
      commission_rate: 0.1,
      enabled: true,
      friend_discount_pct: 10,
      reward_hold_days: 7,
    },
  } satisfies Record<string, unknown>,
  redeemGrowthCodeMock: vi.fn(),
  refetchMock: vi.fn(),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({
    enabled = true,
    queryKey,
  }: {
    enabled?: boolean;
    queryKey: readonly unknown[];
  }) => ({
    data: enabled === false ? undefined : queryFixtures[JSON.stringify(queryKey)],
    isError: false,
    isLoading: false,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations:
    () => (key: string, values?: Record<string, string | number>) => {
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

vi.mock('@/shared/lib/web-vitals', () => ({
  markPerformance: markPerformanceMock,
}));

vi.mock('@/lib/api', () => ({
  growthNotificationsApi: {},
  referralApi: {},
}));

vi.mock('@/features/customer-growth/hooks/useCustomerGrowth', () => ({
  getGrowthRedeemErrorMessage: () => 'redeem-error',
  useGiftCatalogPlans: () => ({
    data: [],
    isLoading: false,
    refetch: refetchMock,
  }),
  useGiftCodes: () => ({
    data: [],
    isLoading: false,
    refetch: refetchMock,
  }),
  useGiftPurchase: () => ({
    isPending: false,
    mutateAsync: giftPurchaseMock,
  }),
  useInviteCodes: () => ({
    data: [],
    isLoading: false,
    refetch: refetchMock,
  }),
  useRedeemGrowthCode: () => ({
    isPending: false,
    mutateAsync: redeemGrowthCodeMock,
  }),
}));

vi.mock(
  '@/features/client-capabilities/useClientCapabilities',
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import('@/features/client-capabilities/useClientCapabilities')
      >();
    return {
      ...actual,
      useClientCapabilities: () => clientCapabilitiesMock,
    };
  },
);

import { ReferralCabinetDashboard } from '../referral-cabinet-dashboard';

beforeEach(() => {
  vi.clearAllMocks();
  clientCapabilitiesMock.data.growth.checkout_code_discounts = false;
  clientCapabilitiesMock.data.growth.gift_codes = false;
  clientCapabilitiesMock.data.growth.growth_hub = true;
  clientCapabilitiesMock.data.growth.invites = false;
  clientCapabilitiesMock.data.growth.promo_codes = false;
  clientCapabilitiesMock.data.growth.referral = true;
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: {
      writeText: copyMock,
    },
  });
  copyMock.mockResolvedValue(undefined);
});

describe('ReferralCabinetDashboard', () => {
  it('renders referral code, reward lifecycle and notifications', async () => {
    render(<ReferralCabinetDashboard />);

    expect(await screen.findByText('CYBER42')).toBeInTheDocument();
    expect(screen.getAllByText('$12').length).toBeGreaterThan(0);
    expect(screen.getByText('Reward pending')).toBeInTheDocument();
    expect(screen.getByText('lifecycle.status.available')).toBeInTheDocument();
    expect(screen.getByText('lifecycle.status.pending')).toBeInTheDocument();
  });

  it('renders the referral route view without growth notifications', async () => {
    render(<ReferralCabinetDashboard view="referral" />);

    expect(await screen.findByText('CYBER42')).toBeInTheDocument();
    expect(screen.getByText('lifecycle.status.available')).toBeInTheDocument();
    expect(screen.queryByText('Reward pending')).not.toBeInTheDocument();
  });

  it('renders the notifications route view without referral share controls', async () => {
    render(<ReferralCabinetDashboard view="notifications" />);

    expect(await screen.findByText('Reward pending')).toBeInTheDocument();
    expect(screen.queryByText('CYBER42')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /share.copyCode/i }),
    ).not.toBeInTheDocument();
  });

  it('does not render gift widgets when gift capabilities are disabled', () => {
    render(<ReferralCabinetDashboard view="gifts" />);

    expect(screen.queryByText('giftPurchase.action')).not.toBeInTheDocument();
    expect(screen.queryByText('giftsTitle')).not.toBeInTheDocument();
  });

  it('copies referral code through the Clipboard API', async () => {
    render(<ReferralCabinetDashboard />);

    await screen.findByText('CYBER42');
    fireEvent.click(screen.getByRole('button', { name: /share.copyCode/i }));

    await waitFor(() => {
      expect(copyMock).toHaveBeenCalledWith('CYBER42');
    });
    expect(markPerformanceMock).toHaveBeenCalledWith('referral-share-copy', {
      kind: 'code',
    });
  });
});
