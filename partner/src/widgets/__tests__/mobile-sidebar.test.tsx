import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, MouseEventHandler, ReactNode } from 'react';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { DASHBOARD_NAV_ITEMS } from '@/widgets/dashboard-navigation';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const mockUsePathname = vi.fn(() => '/dashboard');

vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text, className }: { text: string; className?: string }) => (
    <span className={className}>{text}</span>
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

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

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

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => mockUsePathname(),
  Link: ({
    children,
    href,
    onClick,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    onClick?: MouseEventHandler<HTMLAnchorElement>;
    [key: string]: unknown;
  }) => (
    <a href={href} onClick={onClick} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('@/components/ui/button', () => ({
  Button: forwardRef<
    HTMLButtonElement,
    ButtonHTMLAttributes<HTMLButtonElement> & {
      magnetic?: boolean;
      size?: string;
      variant?: string;
    }
  >(function MockButton(
    { children, magnetic, size, variant, ...props },
    ref,
  ) {
    void magnetic;
    void size;
    void variant;

    return (
      <button ref={ref} type="button" {...props}>
        {children}
      </button>
    );
  }),
}));

import { MobileSidebar } from '../mobile-sidebar';

describe('MobileSidebar', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard');
    mockPortalState.mockReturnValue(
      createPartnerPortalScenarioState(
        'active',
        'reseller_api',
        'workspace_owner',
        'R4',
      ),
    );
  });

  afterEach(() => {
    resetScrollLockForTests();
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
  });

  it('owns a single menu trigger', () => {
    render(<MobileSidebar />);

    expect(screen.getAllByRole('button', { name: 'openMenu' })).toHaveLength(1);
  });

  it('opens as an accessible dialog and renders the full dashboard inventory', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    const dialog = screen.getByRole('dialog', { name: 'sidebar' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: 'closeMenu' })).toHaveFocus();
    expect(screen.getByTestId('partner-workspace-switcher')).toBeInTheDocument();

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(DASHBOARD_NAV_ITEMS.length);
  });

  it('traps focus inside the dialog when tabbing backwards from the close button', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);
    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.getByRole('button', { name: 'closeMenu' })).toHaveFocus();

    await user.tab({ shift: true });

    const lastNavItem = DASHBOARD_NAV_ITEMS[DASHBOARD_NAV_ITEMS.length - 1];
    expect(screen.getByRole('link', { name: lastNavItem.labelKey })).toHaveFocus();
  });

  it('closes on overlay tap and restores document scroll', async () => {
    const user = userEvent.setup();
    const { container } = render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    const backdrop = container.querySelector('div[aria-hidden="true"]');
    expect(backdrop).toBeInTheDocument();

    await user.click(backdrop as HTMLElement);

    expect(
      screen.queryByRole('dialog', { name: 'sidebar' }),
    ).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
    expect(document.documentElement.style.overflow).toBe('');
  });

  it('keeps rollout-gated modules out of the mobile inventory', async () => {
    const user = userEvent.setup();
    mockPortalState.mockReturnValue(
      createPartnerPortalScenarioState(
        'active',
        'creator_affiliate',
        'workspace_owner',
        'R1',
      ),
    );

    render(<MobileSidebar />);
    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.queryByRole('link', { name: 'conversions' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'integrations' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'reseller' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'analytics' })).toBeInTheDocument();
  });
});
