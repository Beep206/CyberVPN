import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import {
  ADMIN_NAV_GROUPS,
  resolveAdminNavigationGroups,
} from '@/features/admin-shell/config/admin-navigation';
import type { AdminNavGroupId } from '@/features/admin-shell/config/admin-navigation';
import { useAuthStore } from '@/stores/auth-store';

const mockUsePathname = vi.fn(() => '/commerce');

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

import { AdminSecondaryNav } from '../admin-secondary-nav';

const DOMAIN_GROUP_IDS: readonly AdminNavGroupId[] = [
  'commerce',
  'growth',
  'infrastructure',
  'security',
  'governance',
  'integrations',
] as const;

function getGroup(groupId: AdminNavGroupId) {
  const group = ADMIN_NAV_GROUPS.find((candidate) => candidate.id === groupId);

  if (!group) {
    throw new Error(`Missing admin navigation group: ${groupId}`);
  }

  return group;
}

describe('AdminSecondaryNav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/commerce');
    useAuthStore.setState({
      user: {
        id: 'admin-1',
        email: 'admin@example.test',
        role: 'super_admin',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00.000Z',
      },
      isAuthenticated: true,
    });
  });

  it.each(DOMAIN_GROUP_IDS)(
    'renders %s links from the shared admin navigation registry',
    (groupId) => {
      const group = getGroup(groupId);

      render(<AdminSecondaryNav groupId={groupId} />);

      expect(
        screen.getByRole('navigation', { name: 'secondaryNavigation' }),
      ).toBeInTheDocument();
      expect(screen.getByText(group.labelKey)).toBeInTheDocument();
      expect(screen.getByText(group.hintKey)).toBeInTheDocument();
      expect(screen.getAllByRole('link')).toHaveLength(group.items.length);

      for (const item of group.items) {
        expect(screen.getByRole('link', { name: item.labelKey })).toHaveAttribute(
          'href',
          item.href,
        );
      }
    },
  );

  it('marks the most specific nested route active without activating overview', () => {
    mockUsePathname.mockReturnValue('/commerce/payments/investigation');

    render(<AdminSecondaryNav groupId="commerce" />);

    expect(screen.getByRole('link', { name: 'item.payments' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      screen.getByRole('link', { name: 'item.commerceOverview' }),
    ).not.toHaveAttribute('aria-current');
  });

  it('marks the overview route active on the exact section root', () => {
    mockUsePathname.mockReturnValue('/security');

    render(<AdminSecondaryNav groupId="security" />);

    expect(
      screen.getByRole('link', { name: 'item.securityOverview' }),
    ).toHaveAttribute('aria-current', 'page');
  });

  it('keeps permission-aware disabled and hidden states from the shared registry', () => {
    useAuthStore.setState({
      user: {
        id: 'finance-1',
        email: 'finance@example.test',
        role: 'finance',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00.000Z',
      },
      isAuthenticated: true,
    });

    render(<AdminSecondaryNav groupId="commerce" />);

    expect(screen.getByRole('link', { name: 'item.payments' })).not.toHaveAttribute(
      'aria-disabled',
    );
    expect(screen.getByRole('link', { name: 'item.plans' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
  });

  it('hides items configured as hidden for the current role', () => {
    useAuthStore.setState({
      user: {
        id: 'finance-1',
        email: 'finance@example.test',
        role: 'finance',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00.000Z',
      },
      isAuthenticated: true,
    });

    render(<AdminSecondaryNav groupId="governance" />);

    expect(
      screen.queryByRole('link', { name: 'item.adminInvites' }),
    ).not.toBeInTheDocument();
    expect(resolveAdminNavigationGroups('finance')).toBeTruthy();
  });

  it('uses item hints as tooltips for compact links', () => {
    render(<AdminSecondaryNav groupId="integrations" />);

    expect(screen.getByRole('link', { name: 'item.telegram' })).toHaveAttribute(
      'title',
      'item.telegramHint',
    );
  });
});
