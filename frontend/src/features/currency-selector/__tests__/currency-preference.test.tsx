import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import {
  CURRENCY_CHANGE_EVENT,
  CURRENCY_COOKIE_NAME,
  CURRENCY_STORAGE_KEY,
  getDefaultCurrencyForLocale,
  isSupportedCurrency,
} from '../currency-config';
import { useCurrencyPreference } from '../use-currency-preference';

describe('currency preference', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.cookie = `${CURRENCY_COOKIE_NAME}=; Max-Age=0; Path=/`;
  });

  it('maps supported launch locales to default display currencies', () => {
    expect(getDefaultCurrencyForLocale('ru-RU')).toBe('RUB');
    expect(getDefaultCurrencyForLocale('en-EN')).toBe('USD');
    expect(getDefaultCurrencyForLocale('zh-Hant')).toBe('TWD');
    expect(getDefaultCurrencyForLocale('unknown-locale')).toBe('USD');
  });

  it('guards unsupported currency values before they reach pricing UI', () => {
    expect(isSupportedCurrency('USD')).toBe(true);
    expect(isSupportedCurrency('RUB')).toBe(true);
    expect(isSupportedCurrency('BTC')).toBe(false);
    expect(isSupportedCurrency(null)).toBe(false);
  });

  it('persists explicit currency changes in local storage and a long-lived cookie', () => {
    const { result } = renderHook(() => useCurrencyPreference('ru-RU'));

    expect(result.current.currency).toBe('RUB');

    act(() => {
      result.current.setCurrency('EUR');
    });

    expect(result.current.currency).toBe('EUR');
    expect(window.localStorage.getItem(CURRENCY_STORAGE_KEY)).toBe('EUR');
    expect(document.cookie).toContain(`${CURRENCY_COOKIE_NAME}=EUR`);
  });

  it('reacts to same-tab and cross-tab preference changes', () => {
    const { result } = renderHook(() => useCurrencyPreference('en-EN'));

    act(() => {
      window.dispatchEvent(new CustomEvent(CURRENCY_CHANGE_EVENT, { detail: { currency: 'KZT' } }));
    });
    expect(result.current.currency).toBe('KZT');

    act(() => {
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: CURRENCY_STORAGE_KEY,
          newValue: 'JPY',
        }),
      );
    });
    expect(result.current.currency).toBe('JPY');

    act(() => {
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: CURRENCY_STORAGE_KEY,
          newValue: null,
        }),
      );
    });
    expect(result.current.currency).toBe('USD');
  });
});
