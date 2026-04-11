import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { INFRASTRUCTURE_NAV_ITEMS } from '@/features/infrastructure/config/navigation';

const mockUsePathname = vi.fn(() => '/infrastructure');

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

import { InfrastructureSubnav } from '../infrastructure-subnav';

describe('InfrastructureSubnav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/infrastructure');
  });

  it('renders the full infrastructure route inventory', () => {
    render(<InfrastructureSubnav />);

    expect(
      screen.getByRole('navigation', { name: 'layout.subnavLabel' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(INFRASTRUCTURE_NAV_ITEMS.length);
  });

  it('marks nested infrastructure routes as active', () => {
    mockUsePathname.mockReturnValue('/infrastructure/node-plugins/history');

    render(<InfrastructureSubnav />);

    expect(
      screen.getByRole('link', { name: 'nav.nodePlugins' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      screen.getByRole('link', { name: 'nav.overview' }),
    ).not.toHaveAttribute('aria-current');
  });
});
