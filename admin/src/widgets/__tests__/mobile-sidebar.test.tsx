import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, MouseEventHandler, ReactNode } from 'react';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { DASHBOARD_NAV_GROUPS } from '@/widgets/dashboard-navigation';
import { useAuthStore } from '@/stores/auth-store';

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

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
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

  afterEach(() => {
    resetScrollLockForTests();
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
  });

  it('owns a single menu trigger', () => {
    render(<MobileSidebar />);

    expect(screen.getAllByRole('button', { name: 'openMenu' })).toHaveLength(1);
  });

  it('opens as an accessible grouped dialog with the active group expanded', async () => {
    const user = userEvent.setup();

    const { container } = render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    const dialog = screen.getByRole('dialog', { name: 'sidebar' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(container).not.toContainElement(dialog);
    expect(document.body).toContainElement(dialog);
    expect(dialog).toHaveClass('z-[80]');
    expect(screen.getByRole('button', { name: 'closeMenu' })).toHaveFocus();
    expect(screen.getAllByRole('button')).toHaveLength(
      DASHBOARD_NAV_GROUPS.length + 2,
    );
    expect(screen.getByRole('button', { name: /group\.operations/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    expect(screen.getByRole('link', { name: 'item.dashboard' })).toHaveAttribute(
      'href',
      '/dashboard',
    );
  });

  it('expands a collapsed group without closing the drawer', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);
    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    await user.click(screen.getByRole('button', { name: /group\.commerce/ }));

    expect(screen.getByRole('button', { name: /group\.commerce/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    expect(screen.getByRole('link', { name: 'item.payments' })).toHaveAttribute(
      'href',
      '/commerce/payments',
    );
    expect(screen.getByRole('dialog', { name: 'sidebar' })).toBeInTheDocument();
  });

  it('shows queue badges inside the mobile drawer when a queued group is expanded', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);
    await user.click(screen.getByRole('button', { name: 'openMenu' }));
    await user.click(screen.getByRole('button', { name: /group\.customers/ }));

    expect(screen.getByLabelText('item.support: 4')).toHaveTextContent('4');
  });

  it('traps focus inside the dialog when tabbing backwards from the close button', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);
    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.getByRole('button', { name: 'closeMenu' })).toHaveFocus();

    await user.tab({ shift: true });

    expect(screen.getByRole('button', { name: /group\.integrations/ })).toHaveFocus();
  });

  it('closes on overlay tap and restores document scroll', async () => {
    const user = userEvent.setup();
    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    const backdrop = document.body.querySelector('div[aria-hidden="true"]');
    expect(backdrop).toBeInTheDocument();
    expect(backdrop).toHaveClass('z-[70]');

    await user.click(backdrop as HTMLElement);

    expect(
      screen.queryByRole('dialog', { name: 'sidebar' }),
    ).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
    expect(document.documentElement.style.overflow).toBe('');
  });
});
