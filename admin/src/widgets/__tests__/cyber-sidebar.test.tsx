import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import {
  DASHBOARD_NAV_GROUPS,
  DASHBOARD_NAV_ITEMS,
} from '@/widgets/dashboard-navigation';
import { useAuthStore } from '@/stores/auth-store';

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

vi.mock('@/features/admin-shell/hooks/use-admin-action-queues', () => ({
  formatAdminQueueBadge: (count: number) => String(count),
  useAdminActionQueues: () => ({
    badges: {
      support: 4,
      'commerce-withdrawals': 8,
    },
    queues: [],
  }),
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
    useAuthStore.setState({
      user: {
        id: 'admin-1',
        email: 'admin@example.test',
        role: 'admin',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00.000Z',
      },
      isAuthenticated: true,
    });
  });

  it('renders grouped navigation and expands the default operations group', () => {
    render(<CyberSidebar />);

    expect(screen.getAllByRole('button')).toHaveLength(
      DASHBOARD_NAV_GROUPS.length,
    );
    expect(screen.getByRole('button', { name: /group\.operations/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    expect(screen.getByRole('link', { name: 'item.dashboard' })).toHaveAttribute(
      'href',
      '/dashboard',
    );
    expect(screen.getAllByTestId('cypher-text').length).toBeGreaterThan(0);
  });

  it('keeps the flat dashboard navigation export available for registry consumers', () => {
    expect(DASHBOARD_NAV_ITEMS.map((item) => item.href)).toContain('/commerce/payments');
  });

  it('marks the most specific active route with aria-current', () => {
    mockUsePathname.mockReturnValue('/commerce/payments');

    render(<CyberSidebar />);

    expect(screen.getByRole('button', { name: /group\.commerce/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    expect(screen.getByRole('link', { name: 'item.payments' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'item.commerceOverview' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('renders queue badges for expanded groups with live counts', () => {
    mockUsePathname.mockReturnValue('/support');

    render(<CyberSidebar />);

    expect(screen.getByRole('button', { name: /group\.customers/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    expect(screen.getByLabelText('item.support: 4')).toHaveTextContent('4');
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
    expect(screen.getAllByText('ADMIN').length).toBeGreaterThan(0);
    expect(screen.getByText('adminConsole')).toBeInTheDocument();
    expect(screen.getAllByText('secureSession').length).toBeGreaterThan(0);
  });
});
