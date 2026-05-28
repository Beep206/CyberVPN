import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CodesSection } from '../CodesSection';

const capabilitiesMock = vi.hoisted(() => ({
  data: {
    growth: {
      checkout_code_discounts: false,
      gift_codes: false,
      growth_hub: false,
      invites: false,
      promo_codes: false,
      referral: false,
    },
  },
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) =>
    (
      ({
        rewardsHubTitle: 'Rewards Hub',
        rewardsHubDescription:
          'Manage invite codes, referral sharing, and invite redemption from one place instead of splitting the flow across subscription screens.',
        rewardsHubCta: 'Open rewards hub',
        checkoutCodesTitle: 'Checkout codes',
        checkoutCodesDescription:
          'Promo codes belong in checkout. Invite redemption stays in the rewards hub so pricing and access do not diverge across surfaces.',
      }) satisfies Record<string, string>
    )[key] ?? key,
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

vi.mock(
  '@/features/client-capabilities/useClientCapabilities',
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import('@/features/client-capabilities/useClientCapabilities')
      >();
    return {
      ...actual,
      useClientCapabilities: () => capabilitiesMock,
    };
  },
);

describe('CodesSection', () => {
  beforeEach(() => {
    capabilitiesMock.data.growth.checkout_code_discounts = false;
    capabilitiesMock.data.growth.gift_codes = false;
    capabilitiesMock.data.growth.growth_hub = false;
    capabilitiesMock.data.growth.invites = false;
    capabilitiesMock.data.growth.promo_codes = false;
    capabilitiesMock.data.growth.referral = false;
  });

  it('hides public rewards and checkout-code guidance while S1 growth flows are disabled', () => {
    render(<CodesSection />);

    expect(screen.queryByText('Rewards Hub')).not.toBeInTheDocument();
    expect(screen.queryByText('Checkout codes')).not.toBeInTheDocument();
  });

  it('renders rewards and checkout-code guidance from runtime capabilities', () => {
    capabilitiesMock.data.growth.invites = true;
    capabilitiesMock.data.growth.checkout_code_discounts = true;
    capabilitiesMock.data.growth.promo_codes = true;

    render(<CodesSection />);

    expect(screen.getByText('Rewards Hub')).toBeInTheDocument();
    expect(screen.getByText('Checkout codes')).toBeInTheDocument();
  });
});
