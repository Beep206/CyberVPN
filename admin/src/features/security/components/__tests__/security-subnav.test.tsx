import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { SECURITY_NAV_ITEMS } from '@/features/security/config/navigation';

const mockUsePathname = vi.fn(() => '/security');

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

import { SecuritySubnav } from '../security-subnav';

describe('SecuritySubnav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/security');
  });

  it('renders the full security route inventory', () => {
    render(<SecuritySubnav />);

    expect(
      screen.getByRole('navigation', { name: 'layout.subnavLabel' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(SECURITY_NAV_ITEMS.length);
    expect(screen.getByRole('link', { name: 'nav.reviewQueue' })).toHaveAttribute(
      'href',
      '/security/review-queue',
    );
  });

  it('marks nested security routes as active', () => {
    mockUsePathname.mockReturnValue('/security/two-factor/backup');

    render(<SecuritySubnav />);

    expect(
      screen.getByRole('link', { name: 'nav.twoFactor' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      screen.getByRole('link', { name: 'nav.overview' }),
    ).not.toHaveAttribute('aria-current');
  });
});
