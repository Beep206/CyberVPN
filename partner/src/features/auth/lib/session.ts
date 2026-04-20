import { normalizeAuthLocale, getDefaultPostLoginPath, localizePathname } from './redirect-path';
import { defaultLocale } from '@/i18n/config';

export const DEFAULT_AUTH_LOCALE = defaultLocale;

const LOCALE_RE = /^\/([a-z]{2,3}-[A-Z]{2})(?:\/|$)/;
const PUBLIC_AUTH_ROUTE_PREFIXES = [
  '/login',
  '/register',
  '/verify',
  '/forgot-password',
  '/reset-password',
  '/magic-link',
  '/oauth',
  '/telegram-link',
] as const;

export function getLocaleFromPathname(pathname: string): string {
  const match = pathname.match(LOCALE_RE);
  return match ? match[1] : DEFAULT_AUTH_LOCALE;
}

function getInternalPathname(rawPathname: string): string {
  const parsed = new URL(rawPathname, 'http://localhost');
  const localeMatch = parsed.pathname.match(LOCALE_RE);

  if (!localeMatch) {
    return parsed.pathname;
  }

  const remainder = parsed.pathname.slice(localeMatch[0].length - 1);
  return remainder || '/';
}

export function isPublicAuthRoute(pathname: string): boolean {
  const internalPathname = getInternalPathname(pathname);

  return PUBLIC_AUTH_ROUTE_PREFIXES.some((routePrefix) => (
    internalPathname === routePrefix || internalPathname.startsWith(`${routePrefix}/`)
  ));
}

export function shouldBootstrapAuthSession(pathname: string): boolean {
  return !isPublicAuthRoute(pathname);
}

/**
 * Builds an external browser URL from a raw pathname like `window.location.pathname`.
 * Do not use this with `@/i18n/navigation`'s `usePathname`, which returns internal,
 * locale-less pathnames.
 */
export function buildLocalizedLoginRedirect(pathname: string): string {
  const locale = getLocaleFromPathname(pathname);
  const redirectTarget = isPublicAuthRoute(pathname)
    ? getDefaultPostLoginPath(locale)
    : localizePathname(pathname, locale);

  return `${localizePathname('/login', locale)}?redirect=${encodeURIComponent(redirectTarget)}`;
}

/**
 * Builds an internal href for `@/i18n/navigation`'s router helpers.
 * The returned href is intentionally locale-less because `next-intl` will
 * apply the active locale prefix automatically.
 */
export function buildInternalLoginHref(pathname: string, locale: string): string {
  const normalizedLocale = normalizeAuthLocale(locale);
  const redirectTarget = isPublicAuthRoute(pathname)
    ? getDefaultPostLoginPath(normalizedLocale)
    : localizePathname(pathname, normalizedLocale);

  return `/login?redirect=${encodeURIComponent(redirectTarget)}`;
}
