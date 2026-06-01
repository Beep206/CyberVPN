import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { useAuthStore } from '@/stores/auth-store';

const navigationMocks = vi.hoisted(() => ({
  pathname: vi.fn(() => '/dashboard'),
  push: vi.fn(),
}));

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => navigationMocks.pathname(),
  useRouter: () => ({
    push: navigationMocks.push,
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

import { AdminCommandPalette } from '../admin-command-palette';

describe('AdminCommandPalette', () => {
  beforeEach(() => {
    navigationMocks.pathname.mockReturnValue('/dashboard');
    navigationMocks.push.mockClear();
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

  it('opens with Ctrl+K, focuses search, and closes with Escape', async () => {
    const user = userEvent.setup();

    render(<AdminCommandPalette />);

    await user.keyboard('{Control>}k{/Control}');

    expect(screen.getByRole('dialog', { name: 'commandPalette.title' })).toBeInTheDocument();
    expect(
      screen.getByRole('combobox', {
        name: 'commandPalette.searchPlaceholder',
      }),
    ).toHaveFocus();
    expect(document.body.style.overflow).toBe('hidden');

    await user.keyboard('{Escape}');

    expect(
      screen.queryByRole('dialog', { name: 'commandPalette.title' }),
    ).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
  });

  it('opens from the trigger and navigates the selected route with Enter', async () => {
    const user = userEvent.setup();

    render(<AdminCommandPalette />);

    await user.click(screen.getByRole('button', { name: 'commandPalette.open' }));
    await user.type(screen.getByRole('combobox'), 'item.support');
    await user.keyboard('{Enter}');

    expect(navigationMocks.push).toHaveBeenCalledWith('/support');
    expect(
      screen.queryByRole('dialog', { name: 'commandPalette.title' }),
    ).not.toBeInTheDocument();
  });

  it('filters results by the current admin role', async () => {
    const user = userEvent.setup();
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

    render(<AdminCommandPalette />);

    await user.keyboard('{Meta>}k{/Meta}');
    await user.type(screen.getByRole('combobox'), 'item.addons');

    expect(screen.queryByRole('option', { name: /item\.addons/ })).not.toBeInTheDocument();
    expect(screen.getByText('commandPalette.empty')).toBeInTheDocument();
  });

  it('does not render raw sensitive search input as a result', async () => {
    const user = userEvent.setup();

    render(<AdminCommandPalette />);

    await user.keyboard('{Control>}k{/Control}');
    await user.type(
      screen.getByRole('combobox'),
      'https://vpn.example.test/subscription/raw-token',
    );

    expect(screen.getByText('commandPalette.empty')).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /raw-token/i })).not.toBeInTheDocument();
  });
});
