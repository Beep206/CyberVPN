import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { DASHBOARD_NAV_ITEMS } from '@/widgets/dashboard-navigation';

vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text, className }: { text: string; className?: string }) => (
    <span data-testid="cypher-text" className={className}>
      {text}
    </span>
  ),
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) =>
    args
      .filter(Boolean)
      .map((value) => (typeof value === 'string' ? value : ''))
      .join(' ')
      .trim(),
}));

const mockUsePathname = vi.fn(() => '/');

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
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

import { CyberSidebar } from '../cyber-sidebar';

describe('CyberSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/');
  });

  it('renders the current dashboard navigation inventory', () => {
    render(<CyberSidebar />);

    const links = screen.getAllByRole('link');
    const cypherTexts = screen.getAllByTestId('cypher-text');

    expect(links).toHaveLength(DASHBOARD_NAV_ITEMS.length);
    expect(cypherTexts).toHaveLength(DASHBOARD_NAV_ITEMS.length);

    for (const item of DASHBOARD_NAV_ITEMS) {
      expect(screen.getByRole('link', { name: item.labelKey })).toHaveAttribute(
        'href',
        item.href,
      );
    }
  });

  it('marks the active route with aria-current', () => {
    mockUsePathname.mockReturnValue('/analytics');

    render(<CyberSidebar />);

    expect(screen.getByRole('link', { name: 'analytics' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'servers' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('stays hidden on mobile and fixed on desktop', () => {
    render(<CyberSidebar />);

    const aside = screen.getByRole('complementary');

    expect(aside).toHaveClass('hidden');
    expect(aside).toHaveClass('md:flex');
    expect(aside).toHaveClass('fixed');
  });

  it('renders the brand and operator block', () => {
    render(<CyberSidebar />);

    expect(screen.getByText('NEXUS')).toBeInTheDocument();
    expect(screen.getByText('ADMIN_01')).toBeInTheDocument();
    expect(screen.getByText('ROOT ACCESS')).toBeInTheDocument();
  });
});
