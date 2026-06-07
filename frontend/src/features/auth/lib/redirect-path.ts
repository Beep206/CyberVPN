import { defaultLocale, locales } from '@/i18n/config';

const AUTH_REDIRECT_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2}\/)?(?:login|register|magic-link|forgot-password|reset-password|verify|oauth\/callback|telegram-link)(?:\/|$)/;
const LOCALE_PREFIX_RE = /^\/(?:[a-z]{2,3}-[A-Z]{2})(\/.*|$)/;
const SUPPORTED_LOCALES = new Set<string>(locales);
const PUBLIC_AUTH_HOSTS = new Set(['cyber-vpn.net', 'www.cyber-vpn.net']);
const CABINET_PRIMARY_HOST = 'my.cyber-vpn.net';
const CABINET_ROUTE_SEGMENTS = new Set([
  'analytics',
  'dashboard',
  'monitoring',
  'partner',
  'payment-history',
  'referral',
  'servers',
  'settings',
  'subscriptions',
  'users',
  'wallet',
]);

export type PostLoginLocation = Pick<Location, 'hostname' | 'port'>;

export function normalizeAuthLocale(locale: string | null | undefined): string {
  if (!locale) {
    return defaultLocale;
  }

  return SUPPORTED_LOCALES.has(locale) ? locale : defaultLocale;
}

export function getDefaultPostLoginPath(locale: string): string {
  return `/${normalizeAuthLocale(locale)}/dashboard`;
}

export function getDefaultMiniAppPath(locale: string): string {
  return `/${normalizeAuthLocale(locale)}/miniapp/home`;
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

function getRouteSegment(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const hasLocale = locales.includes(firstSegment as (typeof locales)[number]);

  return hasLocale ? segments[1] ?? '' : firstSegment ?? '';
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

export function getCanonicalPostLoginHref(
  pathname: string,
  location: PostLoginLocation,
): string | null {
  if (!pathname.startsWith('/') || pathname.startsWith('//')) {
    return null;
  }

  const hostname = (location.hostname || '').toLowerCase().replace(/\.$/, '');
  if (!PUBLIC_AUTH_HOSTS.has(hostname)) {
    return null;
  }

  const parsed = new URL(pathname, 'https://cyber-vpn.net');
  if (!CABINET_ROUTE_SEGMENTS.has(getRouteSegment(parsed.pathname))) {
    return null;
  }

  const canonical = new URL(pathname, `https://${CABINET_PRIMARY_HOST}`);
  if (location.port) {
    canonical.port = location.port;
  }

  return canonical.toString();
}
