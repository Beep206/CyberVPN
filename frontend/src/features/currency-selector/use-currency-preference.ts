'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  CURRENCY_CHANGE_EVENT,
  CURRENCY_COOKIE_NAME,
  CURRENCY_STORAGE_KEY,
  getDefaultCurrencyForLocale,
  isSupportedCurrency,
  type SupportedCurrency,
} from './currency-config';

function readStoredCurrency(): SupportedCurrency | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const stored = window.localStorage.getItem(CURRENCY_STORAGE_KEY);
  return isSupportedCurrency(stored) ? stored : null;
}

function persistCurrency(currency: SupportedCurrency) {
  window.localStorage.setItem(CURRENCY_STORAGE_KEY, currency);
  document.cookie = `${CURRENCY_COOKIE_NAME}=${currency}; Max-Age=31536000; Path=/; SameSite=Lax; Secure`;
  window.dispatchEvent(new CustomEvent(CURRENCY_CHANGE_EVENT, { detail: { currency } }));
}

export function useCurrencyPreference(locale: string) {
  const localeDefaultCurrency = getDefaultCurrencyForLocale(locale);
  const [storedCurrency, setStoredCurrency] = useState<SupportedCurrency | null>(() => readStoredCurrency());
  const currency = storedCurrency ?? localeDefaultCurrency;

  useEffect(() => {
    function handleCurrencyChange(event: Event) {
      const nextCurrency = (event as CustomEvent<{ currency?: unknown }>).detail?.currency;
      if (isSupportedCurrency(nextCurrency)) {
        setStoredCurrency(nextCurrency);
      }
    }

    function handleStorage(event: StorageEvent) {
      if (event.key !== CURRENCY_STORAGE_KEY) {
        return;
      }

      if (isSupportedCurrency(event.newValue)) {
        setStoredCurrency(event.newValue);
      } else if (event.newValue === null) {
        setStoredCurrency(null);
      }
    }

    window.addEventListener(CURRENCY_CHANGE_EVENT, handleCurrencyChange);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener(CURRENCY_CHANGE_EVENT, handleCurrencyChange);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const setCurrency = useCallback((nextCurrency: SupportedCurrency) => {
    setStoredCurrency(nextCurrency);
    persistCurrency(nextCurrency);
  }, []);

  return {
    currency,
    setCurrency,
  };
}
