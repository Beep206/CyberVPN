import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { GOVERNANCE_NAV_ITEMS } from '@/features/governance/config/navigation';

const mockUsePathname = vi.fn(() => '/governance');

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) =>
    args
      .filter(Boolean)
      .map((value) => (typeof value === 'string' ? value : ''))
      .join(' ')
      .trim(),
}));

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => mockUsePathname(),
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

import { GovernanceSubnav } from '../governance-subnav';

describe('GovernanceSubnav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/governance');
  });

  it('renders the full governance route inventory', () => {
    render(<GovernanceSubnav />);

    expect(
      screen.getByRole('navigation', { name: 'layout.subnavLabel' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(GOVERNANCE_NAV_ITEMS.length);
  });

  it('marks nested governance routes as active', () => {
    mockUsePathname.mockReturnValue('/governance/webhook-log/failures');

    render(<GovernanceSubnav />);

    expect(
      screen.getByRole('link', { name: 'nav.webhookLog' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      screen.getByRole('link', { name: 'nav.overview' }),
    ).not.toHaveAttribute('aria-current');
  });
});
