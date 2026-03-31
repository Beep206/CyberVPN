import type { AnchorHTMLAttributes } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PublicTerminalHeader } from '../public-terminal-header';
import { PublicTerminalHeaderControls } from '../public-terminal-header-controls';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: string) => key),
}));

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...props
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/features/theme-toggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

vi.mock('@/features/language-selector', () => ({
  LanguageSelector: () => <div data-testid="language-selector" />,
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
  it('keeps theme and language affordances while rendering static public CTAs', () => {
    render(
      <PublicTerminalHeaderControls
        downloadLabel="Download"
        loginLabel="Sign In"
        registerLabel="Create Account"
      />,
    );

    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
    expect(screen.getByTestId('language-selector')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute(
      'href',
      '/download',
    );
    expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute(
      'data-seo-zone',
      'public_header',
    );
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
});

describe('PublicTerminalHeader', () => {
  async function renderHeader() {
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
    expect(screen.getByRole('link', { name: 'links.download' })).toHaveAttribute(
      'href',
      '/download',
    );
    expect(screen.getAllByRole('link', { name: 'submitButton' })).toHaveLength(2);
    expect(
      screen
        .getAllByRole('link', { name: 'submitButton' })
        .map((link) => link.getAttribute('href')),
    ).toEqual(['/login', '/register']);
  });
});
