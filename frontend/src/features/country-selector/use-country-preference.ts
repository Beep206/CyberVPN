'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  COUNTRY_CHANGE_EVENT,
  COUNTRY_COOKIE_NAME,
  COUNTRY_STORAGE_KEY,
  normalizeCountryCode,
} from './country-config';

function readStoredCountry(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return normalizeCountryCode(window.localStorage.getItem(COUNTRY_STORAGE_KEY));
}

function persistCountry(country: string) {
  window.localStorage.setItem(COUNTRY_STORAGE_KEY, country);
  document.cookie = `${COUNTRY_COOKIE_NAME}=${country}; Max-Age=31536000; Path=/; SameSite=Lax; Secure`;
  window.dispatchEvent(new CustomEvent(COUNTRY_CHANGE_EVENT, { detail: { country } }));
}

export function useCountryPreference(defaultCountry: string) {
  const normalizedDefault = normalizeCountryCode(defaultCountry) ?? 'US';
  const [storedCountry, setStoredCountry] = useState<string | null>(() => readStoredCountry());
  const country = storedCountry ?? normalizedDefault;

  useEffect(() => {
    function handleCountryChange(event: Event) {
      const nextCountry = (event as CustomEvent<{ country?: unknown }>).detail?.country;
      const normalized = normalizeCountryCode(nextCountry);
      if (normalized) {
        setStoredCountry(normalized);
      }
    }

    function handleStorage(event: StorageEvent) {
      if (event.key !== COUNTRY_STORAGE_KEY) {
        return;
      }

      const normalized = normalizeCountryCode(event.newValue);
      setStoredCountry(normalized);
    }

    window.addEventListener(COUNTRY_CHANGE_EVENT, handleCountryChange);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener(COUNTRY_CHANGE_EVENT, handleCountryChange);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const setCountry = useCallback((nextCountry: string) => {
    const normalized = normalizeCountryCode(nextCountry);
    if (!normalized) {
      return;
    }

    setStoredCountry(normalized);
    persistCountry(normalized);
  }, []);

  return {
    country,
    setCountry,
  };
}
