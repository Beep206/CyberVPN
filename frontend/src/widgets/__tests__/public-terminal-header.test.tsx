import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PublicTerminalHeader } from '../public-terminal-header';
import { PublicTerminalHeaderControls } from '../public-terminal-header-controls';
import type { PublicHeaderNavLink } from '../public-terminal-header';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: string) => key),
}));

vi.mock('@/features/theme-toggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

vi.mock('@/features/language-selector', () => ({
  LanguageSelector: () => <div data-testid="language-selector" />,
}));

vi.mock('@/features/currency-selector', () => ({
  CurrencySelector: () => <div data-testid="currency-selector" />,
}));

vi.mock('@/features/header/user-menu', () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}));

let isAuthenticated = false;

const navLinks: PublicHeaderNavLink[] = [
  { href: '/', icon: 'home', label: 'CyberVPN' },
  { href: '/pricing', icon: 'pricing', label: 'Pricing' },
  { href: '/network', icon: 'network', label: 'Network' },
  { href: '/download', icon: 'download', label: 'Download' },
  { href: '/features', icon: 'features', label: 'Features' },
  { href: '/help', icon: 'help', label: 'Help' },
];

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: (selector: (state: { isAuthenticated: boolean }) => unknown) =>
    selector({ isAuthenticated }),
}));

vi.mock('@/widgets/terminal-header-performance', () => ({
  TerminalHeaderPerformance: ({
    fpsLabel,
    pingLabel,
  }: {
    fpsLabel: string;
    pingLabel: string;
  }) => (
    <div data-testid="terminal-header-performance">
      {fpsLabel}:{pingLabel}
    </div>
  ),
}));

describe('PublicTerminalHeaderControls', () => {
  beforeEach(() => {
    isAuthenticated = false;
  });

  it('keeps theme and language affordances while rendering static public CTAs', () => {
    render(
      <PublicTerminalHeaderControls
        downloadLabel="Download"
        loginLabel="Sign In"
        navLinks={navLinks}
        registerLabel="Create Account"
      />,
    );

    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
    expect(screen.getByTestId('language-selector')).toBeInTheDocument();
    expect(screen.getByTestId('currency-selector')).toBeInTheDocument();
    const downloadLinks = screen.getAllByRole('link', { name: 'Download' });
    expect(downloadLinks.some((link) => link.getAttribute('href') === '/download')).toBe(
      true,
    );
    expect(
      downloadLinks.some((link) => link.getAttribute('data-seo-zone') === 'public_header'),
    ).toBe(true);
    expect(screen.getByRole('link', { name: 'Sign In' })).toHaveAttribute(
      'href',
      '/login',
    );
    expect(screen.getByRole('link', { name: 'Sign In' })).toHaveAttribute(
      'data-seo-cta',
      'login',
    );
    expect(screen.getByRole('link', { name: 'Create Account' })).toHaveAttribute(
      'href',
      '/register',
    );
    expect(screen.getByRole('link', { name: 'Create Account' })).toHaveAttribute(
      'data-seo-cta',
      'register',
    );
  });

  it('replaces auth CTAs with profile controls for authenticated users', () => {
    isAuthenticated = true;

    render(
      <PublicTerminalHeaderControls
        downloadLabel="Download"
        loginLabel="Sign In"
        navLinks={navLinks}
        registerLabel="Create Account"
      />,
    );

    expect(screen.queryByRole('link', { name: 'Sign In' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Create Account' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /notifications are not available yet/i })).toBeDisabled();
    expect(screen.getByTestId('user-menu')).toBeInTheDocument();
  });
});

describe('PublicTerminalHeader', () => {
  async function renderHeader() {
    isAuthenticated = false;
    render(await PublicTerminalHeader({ performanceMode: 'always' }));
  }

  it('renders the public shell without dashboard mobile navigation', async () => {
    await renderHeader();

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'openMenu' })).not.toBeInTheDocument();
  });

  it('keeps performance, uplink, and static CTA regions in the public header', async () => {
    await renderHeader();

    expect(screen.getByTestId('terminal-header-performance')).toHaveTextContent(
      'fps:ping',
    );
    expect(screen.getByText('netUplink')).toBeInTheDocument();
    expect(
      screen
        .getAllByRole('link', { name: 'links.download' })
        .some((link) => link.getAttribute('href') === '/download'),
    ).toBe(true);
    expect(screen.getAllByRole('link', { name: 'submitButton' })).toHaveLength(2);
    expect(
      screen
        .getAllByRole('link', { name: 'submitButton' })
        .map((link) => link.getAttribute('href')),
    ).toEqual(['/login', '/register']);
  });
});
