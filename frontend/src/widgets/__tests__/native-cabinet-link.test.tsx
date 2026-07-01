import { afterEach, describe, expect, it, vi } from 'vitest';
import { createEvent, fireEvent, render, screen } from '@testing-library/react';
import type { MouseEventHandler, ReactNode } from 'react';
import { NativeCabinetLink } from '../native-cabinet-link';

const linkNavigateMock = vi.hoisted(() => vi.fn());
const mockUsePathname = vi.hoisted(() => vi.fn(() => '/ru-RU/dashboard'));

vi.mock('next-intl', () => ({
  useLocale: () => 'ru-RU',
}));

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => mockUsePathname(),
  Link: ({
    children,
    href,
    onClick,
    target,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    onClick?: MouseEventHandler<HTMLAnchorElement>;
    target?: string;
    [key: string]: unknown;
  }) => {
    const localizedHref = href.startsWith('/ru-RU') ? href : `/ru-RU${href}`;

    return (
      <a
        href={localizedHref}
        onClick={(event) => {
          onClick?.(event);

          if (
            !event.defaultPrevented &&
            event.button === 0 &&
            !event.altKey &&
            !event.ctrlKey &&
            !event.metaKey &&
            !event.shiftKey &&
            (!target || target === '_self')
          ) {
            event.preventDefault();
            linkNavigateMock(href);
          }
        }}
        target={target}
        {...rest}
      >
        {children}
      </a>
    );
  },
}));

describe('NativeCabinetLink', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    linkNavigateMock.mockClear();
    vi.mocked(window.location.assign).mockClear();
    mockUsePathname.mockReturnValue('/ru-RU/dashboard');
    window.location.href = 'http://localhost:3000';
    window.location.pathname = '/';
    delete process.env.NEXT_PUBLIC_SAFE_CABINET_LINK_FALLBACK;
  });

  it('renders a localized native cabinet href', () => {
    render(<NativeCabinetLink href="/rewards/invites">Invites</NativeCabinetLink>);

    expect(screen.getByRole('link', { name: 'Invites' })).toHaveAttribute(
      'href',
      '/ru-RU/rewards/invites',
    );
  });

  it('uses SPA navigation for plain clicks without scheduling a hard reload', () => {
    const setTimeoutSpy = vi
      .spyOn(window, 'setTimeout')
      .mockImplementation(() => 1 as unknown as ReturnType<typeof setTimeout>);

    render(<NativeCabinetLink href="/wallet">Wallet</NativeCabinetLink>);

    const link = screen.getByRole('link', { name: 'Wallet' });
    const event = createEvent.click(link, { button: 0 });
    fireEvent(link, event);

    expect(event.defaultPrevented).toBe(true);
    expect(linkNavigateMock).toHaveBeenCalledWith('/wallet');
    expect(setTimeoutSpy).not.toHaveBeenCalled();
  });

  it('falls back to document navigation only when explicitly enabled and the path stalls', () => {
    vi.useFakeTimers();
    process.env.NEXT_PUBLIC_SAFE_CABINET_LINK_FALLBACK = 'true';
    window.location.href = 'http://localhost:3000/ru-RU/dashboard';
    window.location.pathname = '/ru-RU/dashboard';

    render(<NativeCabinetLink href="/wallet">Wallet</NativeCabinetLink>);

    fireEvent.click(screen.getByRole('link', { name: 'Wallet' }), {
      button: 0,
    });
    vi.advanceTimersByTime(399);
    expect(window.location.assign).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(window.location.assign).toHaveBeenCalledWith(
      'http://localhost:3000/ru-RU/wallet',
    );
  });

  it('keeps modified clicks native without SPA interception or fallback', () => {
    const setTimeoutSpy = vi
      .spyOn(window, 'setTimeout')
      .mockImplementation(() => 1 as unknown as ReturnType<typeof setTimeout>);

    render(<NativeCabinetLink href="/wallet">Wallet</NativeCabinetLink>);

    fireEvent.click(screen.getByRole('link', { name: 'Wallet' }), {
      button: 0,
      metaKey: true,
    });

    expect(linkNavigateMock).not.toHaveBeenCalled();
    expect(setTimeoutSpy).not.toHaveBeenCalled();
  });
});
