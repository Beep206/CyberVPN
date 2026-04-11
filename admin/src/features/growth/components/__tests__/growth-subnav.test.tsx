import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { GROWTH_NAV_ITEMS } from '@/features/growth/config/navigation';

const mockUsePathname = vi.fn(() => '/growth');

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

import { GrowthSubnav } from '../growth-subnav';

describe('GrowthSubnav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/growth');
  });

  it('renders the full growth route inventory', () => {
    render(<GrowthSubnav />);

    expect(
      screen.getByRole('navigation', { name: 'layout.subnavLabel' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(GROWTH_NAV_ITEMS.length);
  });

  it('marks nested growth routes as active', () => {
    mockUsePathname.mockReturnValue('/growth/promo-codes/active');

    render(<GrowthSubnav />);

    expect(
      screen.getByRole('link', { name: 'nav.promoCodes' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      screen.getByRole('link', { name: 'nav.overview' }),
    ).not.toHaveAttribute('aria-current');
  });
});
