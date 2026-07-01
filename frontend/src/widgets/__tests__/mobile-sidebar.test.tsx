import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, MouseEventHandler, ReactNode } from 'react';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { getWebCabinetNavigationSections } from '@/widgets/dashboard-navigation';

const mockUsePathname = vi.fn(() => '/dashboard');
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

vi.mock('next-intl', () => ({
  useLocale: () => 'ru-RU',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({
    push: vi.fn(),
  }),
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
    <a
      href={href.startsWith('/ru-RU') ? href : `/ru-RU${href}`}
      onClick={onClick}
      {...rest}
    >
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

vi.mock('@/components/ui/button', () => ({
  Button: forwardRef<
    HTMLButtonElement,
    ButtonHTMLAttributes<HTMLButtonElement> & {
      magnetic?: boolean;
      size?: string;
      variant?: string;
    }
  >(function MockButton({ children, magnetic, size, variant, ...props }, ref) {
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
    clientCapabilitiesMock.data.growth.checkout_code_discounts = false;
    clientCapabilitiesMock.data.growth.gift_codes = false;
    clientCapabilitiesMock.data.growth.growth_hub = false;
    clientCapabilitiesMock.data.growth.invites = false;
    clientCapabilitiesMock.data.growth.promo_codes = false;
    clientCapabilitiesMock.data.growth.referral = false;
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

  it('opens as an accessible dialog and renders the web cabinet inventory', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    const dialog = screen.getByRole('dialog', { name: 'sidebar' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveClass('h-dvh');
    expect(dialog.parentElement).toBe(document.body);
    expect(screen.getByRole('button', { name: 'closeMenu' })).toHaveFocus();

    const navItems = getWebCabinetNavigationSections({
      capabilities: clientCapabilitiesMock.data,
    }).flatMap((section) => section.items);
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(navItems.length);
    expect(links.map((link) => link.getAttribute('href'))).toEqual(
      navItems.map((item) => `/ru-RU${item.href}`),
    );
  });

  it('uses the same rewards routes as the desktop cabinet when growth is enabled', async () => {
    clientCapabilitiesMock.data.growth.checkout_code_discounts = true;
    clientCapabilitiesMock.data.growth.gift_codes = true;
    clientCapabilitiesMock.data.growth.growth_hub = true;
    clientCapabilitiesMock.data.growth.invites = true;
    clientCapabilitiesMock.data.growth.promo_codes = true;
    clientCapabilitiesMock.data.growth.referral = true;
    const user = userEvent.setup();

    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.getByRole('link', { name: 'items.invites' })).toHaveAttribute(
      'href',
      '/ru-RU/rewards/invites',
    );
    expect(screen.getByRole('link', { name: 'items.codes' })).toHaveAttribute(
      'href',
      '/ru-RU/rewards/codes',
    );
    expect(screen.queryByRole('link', { name: 'referral' })).not.toBeInTheDocument();
  });

  it('does not expose hidden rewards routes when growth is disabled', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.queryByRole('link', { name: 'items.rewards' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'items.invites' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'items.codes' })).not.toBeInTheDocument();
  });

  it('matches active routes by path segments instead of substring containment', async () => {
    mockUsePathname.mockReturnValue('/wallets');
    const user = userEvent.setup();

    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.getByRole('link', { name: 'items.wallet' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('closes the drawer after selecting a cabinet route', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));
    await user.click(screen.getByRole('link', { name: 'items.wallet' }));

    expect(
      screen.queryByRole('dialog', { name: 'sidebar' }),
    ).not.toBeInTheDocument();
  });

  it('traps focus inside the dialog when tabbing backwards from the close button', async () => {
    const user = userEvent.setup();

    render(<MobileSidebar />);
    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(screen.getByRole('button', { name: 'closeMenu' })).toHaveFocus();

    await user.tab({ shift: true });

    expect(screen.getByRole('link', { name: 'items.security' })).toHaveFocus();
  });

  it('closes on overlay tap and restores document scroll', async () => {
    const user = userEvent.setup();
    render(<MobileSidebar />);

    await user.click(screen.getByRole('button', { name: 'openMenu' }));

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    const backdrop = document.body.querySelector(
      '[data-cy-overlay="mobile-sidebar-backdrop"]',
    );
    expect(backdrop).toBeInTheDocument();

    await user.click(backdrop as HTMLElement);

    expect(
      screen.queryByRole('dialog', { name: 'sidebar' }),
    ).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
    expect(document.documentElement.style.overflow).toBe('');
  });
});
