import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CURRENCY_STORAGE_KEY } from '@/features/currency-selector/currency-config';
import { TerminalHeaderControls } from '../terminal-header-controls';

const { authState } = vi.hoisted(() => ({
  authState: {
    isAuthenticated: true,
    isLoading: false,
  },
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/features/theme-toggle', () => ({
  ThemeToggle: () => <button type="button" aria-label="theme" />,
}));

vi.mock('@/features/language-selector', () => ({
  LanguageSelector: () => <button type="button" aria-label="language" />,
}));

vi.mock('@/features/header/qr-code-dropdown', () => ({
  QRCodeDropdown: () => <button type="button" aria-label="get app" />,
}));

vi.mock('@/features/header/user-menu', () => ({
  UserMenu: () => <button type="button" aria-label="user menu" />,
}));

vi.mock('@/features/notifications/notification-dropdown', () => ({
  NotificationDropdown: () => <button type="button" aria-label="notifications" />,
}));

describe('TerminalHeaderControls', () => {
  beforeEach(() => {
    authState.isAuthenticated = true;
    authState.isLoading = false;
    window.localStorage.clear();
  });

  it('renders the visual currency selector for authenticated customer header controls', () => {
    window.localStorage.setItem(CURRENCY_STORAGE_KEY, 'RUB');

    render(
      <TerminalHeaderControls
        loginLabel="Sign In"
        registerLabel="Create Account"
      />,
    );

    const currencyTrigger = screen.getByRole('button', {
      name: 'Select currency: Russian Ruble',
    });

    expect(currencyTrigger).toHaveTextContent('₽');
    expect(currencyTrigger).not.toHaveTextContent('RUB');
    expect(currencyTrigger).not.toHaveTextContent('USD');
    expect(screen.getByRole('button', { name: 'user menu' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'notifications' })).toBeInTheDocument();
  });
});
