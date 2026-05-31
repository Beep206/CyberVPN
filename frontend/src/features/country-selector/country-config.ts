export const COUNTRY_STORAGE_KEY = 'cybervpn.country';
export const COUNTRY_COOKIE_NAME = 'cybervpn_country';
export const COUNTRY_CHANGE_EVENT = 'cybervpn:country-change';

const COUNTRY_CODE_RE = /^[A-Z]{2}$/;

export function isSupportedCountryCode(value: unknown): value is string {
  return typeof value === 'string' && COUNTRY_CODE_RE.test(value);
}

export function normalizeCountryCode(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim().toUpperCase();
  return isSupportedCountryCode(normalized) ? normalized : null;
}
