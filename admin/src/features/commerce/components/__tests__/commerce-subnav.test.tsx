import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { COMMERCE_NAV_ITEMS } from '@/features/commerce/config/navigation';

const mockUsePathname = vi.fn(() => '/commerce');

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

import { CommerceSubnav } from '../commerce-subnav';

describe('CommerceSubnav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/commerce');
  });

  it('renders the full commerce route inventory', () => {
    render(<CommerceSubnav />);

    expect(
      screen.getByRole('navigation', { name: 'layout.subnavLabel' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(COMMERCE_NAV_ITEMS.length);
  });

  it('marks the active subsection for nested routes', () => {
    mockUsePathname.mockReturnValue('/commerce/payments/investigation');

    render(<CommerceSubnav />);

    expect(screen.getByRole('link', { name: 'nav.payments' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'nav.overview' })).not.toHaveAttribute(
      'aria-current',
    );
  });
});
