import { defaultLocale, locales } from '@/i18n/config';

const AUTH_REDIRECT_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2}\/)?(?:login|register|magic-link|forgot-password|reset-password|verify|oauth\/callback|telegram-link)(?:\/|$)/;
const SUPPORTED_LOCALES = new Set<string>(locales);

export function normalizeAuthLocale(locale: string | null | undefined): string {
  if (!locale) {
    return defaultLocale;
  }

  return SUPPORTED_LOCALES.has(locale) ? locale : defaultLocale;
}

export function getDefaultPostLoginPath(locale: string): string {
  return `/${normalizeAuthLocale(locale)}/dashboard`;
}

export function getSafeRedirectPath(rawRedirect: string | null, locale: string): string {
  const fallback = getDefaultPostLoginPath(locale);

  if (!rawRedirect) {
    return fallback;
  }

  let candidate = rawRedirect;
  try {
    candidate = decodeURIComponent(rawRedirect);
  } catch {
    return fallback;
  }

  const isRelativePath = candidate.startsWith('/') && !candidate.startsWith('//');
  if (!isRelativePath) {
    return fallback;
  }

  if (AUTH_REDIRECT_RE.test(candidate)) {
    return fallback;
  }

  return candidate;
}
