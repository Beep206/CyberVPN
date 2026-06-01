import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { getWebCabinetNavigationSections } from '@/widgets/dashboard-navigation';

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
const clientCapabilitiesMock = vi.hoisted(() => ({
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

vi.mock(
  '@/features/client-capabilities/useClientCapabilities',
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import('@/features/client-capabilities/useClientCapabilities')
      >();
    return {
      ...actual,
      useClientCapabilities: () => clientCapabilitiesMock,
    };
  },
);

import { CyberSidebar } from '../cyber-sidebar';

describe('CyberSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/');
    clientCapabilitiesMock.data.growth.checkout_code_discounts = false;
    clientCapabilitiesMock.data.growth.gift_codes = false;
    clientCapabilitiesMock.data.growth.growth_hub = false;
    clientCapabilitiesMock.data.growth.invites = false;
    clientCapabilitiesMock.data.growth.promo_codes = false;
    clientCapabilitiesMock.data.growth.referral = false;
  });

  it('renders the current dashboard navigation inventory', () => {
    render(<CyberSidebar />);

    const navItems = getWebCabinetNavigationSections({
      capabilities: clientCapabilitiesMock.data,
    }).flatMap((section) => section.items);
    const links = screen.getAllByRole('link');
    const cypherTexts = screen.getAllByTestId('cypher-text');

    expect(links).toHaveLength(navItems.length);
    expect(cypherTexts).toHaveLength(navItems.length);

    for (const item of navItems) {
      expect(screen.getByRole('link', { name: item.labelKey })).toHaveAttribute(
        'href',
        item.href,
      );
    }
  });

  it('marks the active route with aria-current', () => {
    mockUsePathname.mockReturnValue('/wallet');

    render(<CyberSidebar />);

    expect(screen.getByRole('link', { name: 'items.wallet' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      screen.getByRole('link', { name: 'items.vpnAccess' }),
    ).not.toHaveAttribute('aria-current');
  });

  it('renders rewards as a section with split child routes when growth capabilities are enabled', () => {
    clientCapabilitiesMock.data.growth.growth_hub = true;
    clientCapabilitiesMock.data.growth.gift_codes = true;
    clientCapabilitiesMock.data.growth.invites = true;
    clientCapabilitiesMock.data.growth.referral = true;

    render(<CyberSidebar />);

    expect(screen.getByText('sections.growth')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'items.rewards' })).toHaveAttribute(
      'href',
      '/rewards',
    );
    expect(screen.getByRole('link', { name: 'items.referral' })).toHaveAttribute(
      'href',
      '/rewards/referral',
    );
    expect(screen.getByRole('link', { name: 'items.gifts' })).toHaveAttribute(
      'href',
      '/rewards/gifts',
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
    expect(screen.getByText('USER NODE')).toBeInTheDocument();
    expect(screen.getByText('PRIVATE ACCESS')).toBeInTheDocument();
  });
});
