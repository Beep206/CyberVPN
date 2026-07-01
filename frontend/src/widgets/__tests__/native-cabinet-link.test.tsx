import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { NativeCabinetLink } from '../native-cabinet-link';

vi.mock('next-intl', () => ({
  useLocale: () => 'ru-RU',
}));

describe('NativeCabinetLink', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a localized native cabinet href', () => {
    render(<NativeCabinetLink href="/rewards/invites">Invites</NativeCabinetLink>);

    expect(screen.getByRole('link', { name: 'Invites' })).toHaveAttribute(
      'href',
      '/ru-RU/rewards/invites',
    );
  });

  it('schedules same-window navigation fallback for plain clicks', () => {
    const setTimeoutSpy = vi
      .spyOn(window, 'setTimeout')
      .mockImplementation(() => 1 as unknown as ReturnType<typeof setTimeout>);

    render(<NativeCabinetLink href="/wallet">Wallet</NativeCabinetLink>);

    fireEvent.click(screen.getByRole('link', { name: 'Wallet' }), {
      button: 0,
    });

    expect(setTimeoutSpy).toHaveBeenCalledTimes(1);
  });

  it('keeps modified clicks native without scheduling same-window fallback', () => {
    const setTimeoutSpy = vi
      .spyOn(window, 'setTimeout')
      .mockImplementation(() => 1 as unknown as ReturnType<typeof setTimeout>);

    render(<NativeCabinetLink href="/wallet">Wallet</NativeCabinetLink>);

    fireEvent.click(screen.getByRole('link', { name: 'Wallet' }), {
      button: 0,
      metaKey: true,
    });

    expect(setTimeoutSpy).not.toHaveBeenCalled();
  });
});
