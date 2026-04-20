import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { DASHBOARD_NAV_ITEMS } from '@/widgets/dashboard-navigation';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

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

const mockPortalState = vi.fn<() => PartnerPortalState>(() => (
  createPartnerPortalScenarioState(
    'active',
    'reseller_api',
    'workspace_owner',
    'R4',
  )
));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state', () => ({
  usePartnerPortalBootstrapState: () => ({
    state: mockPortalState(),
    bootstrap: null,
    activeWorkspace: null,
    workspaces: [],
    activeWorkspaceId: null,
    isCanonicalWorkspace: false,
    isSimulationEnabled: false,
    workspaceSelection: null,
    queries: {
      bootstrapQuery: null,
      workspacesQuery: null,
    },
  }),
}));

vi.mock('@/features/partner-portal-state/components/partner-workspace-switcher', () => ({
  PartnerWorkspaceSwitcher: () => (
    <div data-testid="partner-workspace-switcher">workspace-switcher</div>
  ),
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (selector: (state: { user: { login: string; email: string } }) => unknown) =>
    selector({ user: { login: 'partner.ops', email: 'partner.ops@example.com' } }),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
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
    mockPortalState.mockReturnValue(
      createPartnerPortalScenarioState(
        'active',
        'reseller_api',
        'workspace_owner',
        'R4',
      ),
    );
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

  it('hides rollout-gated modules from the sidebar inventory', () => {
    mockPortalState.mockReturnValue(
      createPartnerPortalScenarioState(
        'active',
        'creator_affiliate',
        'workspace_owner',
        'R1',
      ),
    );

    render(<CyberSidebar />);

    expect(screen.queryByRole('link', { name: 'conversions' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'integrations' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'reseller' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'analytics' })).toBeInTheDocument();
  });

  it('marks the active route with aria-current', () => {
    mockUsePathname.mockReturnValue('/dashboard');

    render(<CyberSidebar />);

    expect(screen.getByRole('link', { name: 'dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
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

    expect(screen.getByText('OZOXY')).toBeInTheDocument();
    expect(screen.getAllByText('PARTNER').length).toBeGreaterThan(0);
    expect(screen.getByTestId('partner-workspace-switcher')).toBeInTheDocument();
    expect(screen.getByText('adminConsole')).toBeInTheDocument();
    expect(screen.getAllByText('secureSession').length).toBeGreaterThan(0);
  });
});
