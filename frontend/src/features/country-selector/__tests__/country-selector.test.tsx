import { act, render, renderHook, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  COUNTRY_CHANGE_EVENT,
  COUNTRY_COOKIE_NAME,
  COUNTRY_STORAGE_KEY,
  normalizeCountryCode,
} from '../country-config';
import { CountrySelector } from '../country-selector';
import { useCountryPreference } from '../use-country-preference';

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => {
    const labels: Record<string, string> = {
      'countrySelector.aria': 'Select country',
      'countrySelector.empty': 'No country found',
      'countrySelector.search': 'SEARCH_COUNTRY...',
      'countrySelector.searchAria': 'Search countries',
      'countrySelector.title': 'SELECT_COUNTRY',
    };
    return (key: string) => labels[key] ?? key;
  },
}));

vi.mock('@/shared/ui/country-flag', () => ({
  CountryFlag: ({ code }: { code: string }) => <span data-testid={`flag-${code}`}>{code}</span>,
}));

vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => children,
}));

describe('country selector', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.cookie = `${COUNTRY_COOKIE_NAME}=; Max-Age=0; Path=/`;
  });

  it('normalizes only ISO-like country codes', () => {
    expect(normalizeCountryCode('de')).toBe('DE');
    expect(normalizeCountryCode('USA')).toBeNull();
    expect(normalizeCountryCode(null)).toBeNull();
  });

  it('persists explicit country changes independently from locale', () => {
    const { result } = renderHook(() => useCountryPreference('US'));

    expect(result.current.country).toBe('US');

    act(() => {
      result.current.setCountry('DE');
    });

    expect(result.current.country).toBe('DE');
    expect(window.localStorage.getItem(COUNTRY_STORAGE_KEY)).toBe('DE');
    expect(document.cookie).toContain(`${COUNTRY_COOKIE_NAME}=DE`);
  });

  it('renders selectable backend countries and notifies caller after selection', async () => {
    const user = userEvent.setup();
    const onCountryChange = vi.fn();

    render(
      <CountrySelector
        countries={['US', 'DE']}
        defaultCountry="US"
        onCountryChange={onCountryChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Select country: US' }));
    await user.click(screen.getByRole('button', { name: /DE Germany/i }));

    expect(onCountryChange).toHaveBeenCalledWith('DE');
    expect(window.localStorage.getItem(COUNTRY_STORAGE_KEY)).toBe('DE');
  });

  it('reacts to same-tab country preference events', () => {
    const { result } = renderHook(() => useCountryPreference('US'));

    act(() => {
      window.dispatchEvent(new CustomEvent(COUNTRY_CHANGE_EVENT, { detail: { country: 'FR' } }));
    });

    expect(result.current.country).toBe('FR');
  });
});
