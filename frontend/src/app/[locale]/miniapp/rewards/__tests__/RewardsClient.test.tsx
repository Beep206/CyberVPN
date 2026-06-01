import { render, screen } from '@testing-library/react';
import type { AnchorHTMLAttributes, HTMLAttributes } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { MiniAppRewardsRoute } from '../RewardsClient';

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('next/dynamic', () => ({
  default: () => () => <div data-testid="qr-code" />,
}));

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    href,
    children,
    className,
    ...props
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('../../hooks/useTelegramWebApp', () => ({
  useTelegramWebApp: () => ({
    haptic: vi.fn(),
    hapticNotification: vi.fn(),
    webApp: {
      openLink: vi.fn(),
      openTelegramLink: vi.fn(),
      showAlert: vi.fn(),
    },
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
      useClientCapabilities: () => ({
        data: {
          growth: {
            checkout_code_discounts: true,
            gift_codes: true,
            growth_hub: true,
            invites: true,
            promo_codes: true,
            referral: true,
          },
        },
        isLoading: false,
        isError: false,
      }),
    };
  },
);

vi.mock('@/features/customer-growth/components/GrowthNotificationsPanel', () => ({
  GrowthNotificationsPanel: () => <section data-testid="notifications-panel" />,
}));

vi.mock(
  '@/features/customer-growth/components/GrowthNotificationPreferencesPanel',
  () => ({
    GrowthNotificationPreferencesPanel: () => (
      <section data-testid="notification-preferences-panel" />
    ),
  }),
);

vi.mock('@/features/customer-growth/hooks/useCustomerGrowth', () => {
  const mutationMock = () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  });

  return {
    getGrowthNotificationRecoveryErrorMessage: () => 'recovery failed',
    getGrowthNotificationSupportEscalationErrorMessage: () => 'support failed',
    getGrowthRedeemErrorMessage: () => 'redeem failed',
    useArchiveGrowthNotification: mutationMock,
    useGiftCatalogPlans: () => ({ data: [], isLoading: false }),
    useGiftCodes: () => ({ data: [], isLoading: false }),
    useGiftPurchase: mutationMock,
    useGrowthNotificationCounters: () => ({ data: {} }),
    useGrowthNotificationDetail: () => ({ data: null, isLoading: false }),
    useGrowthNotifications: () => ({ data: [], isLoading: false }),
    useGrowthNotificationPreferences: () => ({ data: null, isLoading: false }),
    useInviteCodes: () => ({ data: [], isLoading: false }),
    useMarkGrowthNotificationRead: mutationMock,
    useRecentReferralActivity: () => ({ data: [], isLoading: false }),
    useRedeemGrowthCode: mutationMock,
    useReferralCode: () => ({
      data: { referral_code: 'REF123' },
      isLoading: false,
    }),
    useReferralStats: () => ({
      data: {
        commission_rate: 10,
        total_earned: 25,
        total_referrals: 3,
      },
      isLoading: false,
    }),
    useReferralStatus: () => ({
      data: { commission_rate: 10, enabled: true },
      isLoading: false,
    }),
    useRequestGrowthNotificationRecovery: mutationMock,
    useRequestGrowthNotificationSupportEscalation: mutationMock,
    useUpdateGrowthNotificationPreferences: mutationMock,
  };
});

describe('MiniAppRewardsRoute', () => {
  it('renders rewards chips with mobile-safe 44px touch targets', () => {
    render(<MiniAppRewardsRoute view="overview" />);

    const nav = screen.getByLabelText('rewards.navigationLabel');
    const chips = Array.from(nav.querySelectorAll('a'));

    expect(chips).toHaveLength(6);
    expect(chips.map((chip) => chip.getAttribute('href'))).toEqual([
      '/miniapp/rewards',
      '/miniapp/rewards/referral',
      '/miniapp/rewards/gifts',
      '/miniapp/rewards/invites',
      '/miniapp/rewards/codes',
      '/miniapp/rewards/notifications',
    ]);

    for (const chip of chips) {
      expect(chip).toHaveClass('min-h-11');
      expect(chip).toHaveClass('inline-flex');
      expect(chip).toHaveClass('whitespace-nowrap');
      expect(chip).toHaveClass('touch-manipulation');
    }
  });
});
