import { afterEach, describe, expect, it, vi } from 'vitest';
import { createEvent, fireEvent, render, screen } from '@testing-library/react';
import { NativeCabinetLink } from '../native-cabinet-link';

const routerPushMock = vi.hoisted(() => vi.fn());

vi.mock('next-intl', () => ({
  useLocale: () => 'ru-RU',
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: routerPushMock,
  }),
}));

describe('NativeCabinetLink', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    routerPushMock.mockClear();
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
    expect(routerPushMock).toHaveBeenCalledWith('/ru-RU/wallet');
    expect(setTimeoutSpy).not.toHaveBeenCalled();
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

    expect(routerPushMock).not.toHaveBeenCalled();
    expect(setTimeoutSpy).not.toHaveBeenCalled();
  });
});
