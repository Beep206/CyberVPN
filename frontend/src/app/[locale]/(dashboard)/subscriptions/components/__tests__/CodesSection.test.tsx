import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CodesSection } from '../CodesSection';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) =>
    (
      {
        rewardsHubTitle: 'Rewards Hub',
        rewardsHubDescription:
          'Manage invite codes, referral sharing, and invite redemption from one place instead of splitting the flow across subscription screens.',
        rewardsHubCta: 'Open rewards hub',
        checkoutCodesTitle: 'Checkout codes',
        checkoutCodesDescription:
          'Promo codes belong in checkout. Invite redemption stays in the rewards hub so pricing and access do not diverge across surfaces.',
      } satisfies Record<string, string>
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

describe('CodesSection', () => {
  it('renders a single entry point to the rewards hub', () => {
    render(<CodesSection />);

    expect(screen.getByText('Rewards Hub')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Manage invite codes, referral sharing, and invite redemption from one place instead of splitting the flow across subscription screens.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open rewards hub/i })).toHaveAttribute(
      'href',
      '/referral',
    );
  });

  it('keeps promo guidance inside the subscriptions surface', () => {
    render(<CodesSection />);

    expect(screen.getByText('Checkout codes')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Promo codes belong in checkout. Invite redemption stays in the rewards hub so pricing and access do not diverge across surfaces.',
      ),
    ).toBeInTheDocument();
  });
});
