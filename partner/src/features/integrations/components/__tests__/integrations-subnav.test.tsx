import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { INTEGRATIONS_NAV_ITEMS } from '@/features/integrations/config/navigation';

const mockUsePathname = vi.fn(() => '/integrations');

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

import { IntegrationsSubnav } from '../integrations-subnav';

describe('IntegrationsSubnav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/integrations');
  });

  it('renders the full integrations route inventory', () => {
    render(<IntegrationsSubnav />);

    expect(
      screen.getByRole('navigation', { name: 'layout.subnavLabel' }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(INTEGRATIONS_NAV_ITEMS.length);
  });

  it('marks nested integrations routes as active', () => {
    mockUsePathname.mockReturnValue('/integrations/realtime/live');

    render(<IntegrationsSubnav />);

    expect(
      screen.getByRole('link', { name: 'nav.realtime' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      screen.getByRole('link', { name: 'nav.overview' }),
    ).not.toHaveAttribute('aria-current');
  });
});
