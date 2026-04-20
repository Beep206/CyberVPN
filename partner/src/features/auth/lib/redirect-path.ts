import { defaultLocale, locales } from '@/i18n/config';

const AUTH_REDIRECT_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2}\/)?login(?:\/|$)/;
const LOCALE_PREFIX_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2})(\/.*|$)/;
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

function stripLocalePrefix(pathname: string): string {
  const match = pathname.match(LOCALE_PREFIX_RE);
  if (!match) {
    return pathname;
  }

  return match[1] || '/';
}

export function localizePathname(pathname: string, locale: string): string {
  const normalizedLocale = normalizeAuthLocale(locale);

  if (!pathname.startsWith('/')) {
    return getDefaultPostLoginPath(normalizedLocale);
  }

  const parsed = new URL(pathname, 'http://localhost');
  const basePathname = stripLocalePrefix(parsed.pathname);
  const localizedPathname = basePathname === '/'
    ? `/${normalizedLocale}`
    : `/${normalizedLocale}${basePathname}`;

  return `${localizedPathname}${parsed.search}${parsed.hash}`;
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

  return localizePathname(candidate, locale);
}
