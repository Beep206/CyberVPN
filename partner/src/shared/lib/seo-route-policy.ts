import { defaultLocale, locales } from '@/i18n/config';
import {
  getIndexableLocalesForPath,
  isLocaleIndexableForPath,
} from '@/shared/lib/locale-rollout-policy';

const DEFAULT_DEV_SITE_URL = 'http://localhost:3002';
const DEFAULT_PROD_SITE_URL = 'https://partner.ozoxy.ru';

function normalizeSiteUrl(value: string): string {
  return value.replace(/\/+$/, '');
}

export const SITE_URL = normalizeSiteUrl(
  process.env.NEXT_PUBLIC_SITE_URL ??
    (process.env.NODE_ENV === 'development' ? DEFAULT_DEV_SITE_URL : DEFAULT_PROD_SITE_URL),
);

export type LocalizedPathInfo = {
  locale?: (typeof locales)[number];
  pathname: string;
  isLocalized: boolean;
};

export const INDEXABLE_MARKETING_PATHS = [
  '/',
  '/api',
  '/audits',
  '/compare',
  '/contact',
  '/devices',
  '/docs',
  '/download',
  '/features',
  '/guides',
  '/help',
  '/network',
  '/pricing',
  '/privacy',
  '/privacy-policy',
  '/security',
  '/status',
  '/terms',
  '/trust',
] as const;

export const INDEXABLE_MARKETING_PREFIXES = ['/compare', '/devices', '/guides'] as const;

export const CLIENT_PORTAL_PATH_PREFIXES = [
  '/analytics',
  '/dashboard',
  '/monitoring',
  '/partner',
  '/payment-history',
  '/referral',
  '/servers',
  '/settings',
  '/subscriptions',
  '/users',
  '/wallet',
] as const;

export const NOINDEX_PATH_PREFIXES = [
  ...CLIENT_PORTAL_PATH_PREFIXES,
  '/forgot-password',
  '/login',
  '/magic-link',
  '/miniapp',
  '/oauth',
  '/register',
  '/reset-password',
  '/telegram-link',
  '/telegram-widget',
] as const;

export const NOINDEX_EXACT_PATHS = ['/test-animation', '/test-error'] as const;

function normalizePathname(pathname: string): string {
  if (!pathname) return '/';

  const trimmed = pathname.trim();
  if (!trimmed) return '/';

  const normalized = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  if (normalized === '/') return normalized;

  return normalized.replace(/\/+$/, '');
}

function isLocaleSegment(segment: string): segment is (typeof locales)[number] {
  return locales.includes(segment as (typeof locales)[number]);
}

export function getLocalizedPathInfo(pathname: string): LocalizedPathInfo {
  const normalized = normalizePathname(pathname);
  const [, firstSegment = '', ...rest] = normalized.split('/');

  if (isLocaleSegment(firstSegment)) {
    const localizedPath = `/${rest.join('/')}`;

    return {
      locale: firstSegment,
      pathname: localizedPath === '/' ? '/' : localizedPath.replace(/\/+$/, ''),
      isLocalized: true,
    };
  }

  return {
    pathname: normalized,
    isLocalized: false,
  };
}

export function toLocalizedPath(
  locale: (typeof locales)[number],
  pathname: string,
): string {
  const { pathname: normalizedPath } = getLocalizedPathInfo(pathname);

  if (normalizedPath === '/') {
    return `/${locale}`;
  }

  return `/${locale}${normalizedPath}`;
}

export function toAbsoluteLocalizedUrl(
  locale: (typeof locales)[number],
  pathname: string,
): string {
  return new URL(toLocalizedPath(locale, pathname), SITE_URL).toString();
}

function isNoindexPath(pathname: string): boolean {
  return (
    NOINDEX_EXACT_PATHS.includes(pathname as (typeof NOINDEX_EXACT_PATHS)[number]) ||
    NOINDEX_PATH_PREFIXES.some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    )
  );
}

function isIndexablePath(pathname: string): boolean {
  if (
    INDEXABLE_MARKETING_PATHS.includes(
      pathname as (typeof INDEXABLE_MARKETING_PATHS)[number],
    )
  ) {
    return true;
  }

  return INDEXABLE_MARKETING_PREFIXES.some(
    (prefix) => pathname.startsWith(`${prefix}/`),
  );
}

export function isIndexableLocalizedPath(pathname: string): boolean {
  const { pathname: normalizedPath } = getLocalizedPathInfo(pathname);

  if (isNoindexPath(normalizedPath)) {
    return false;
  }

  return isIndexablePath(normalizedPath);
}

export function isRolloutIndexableLocalizedPath(pathname: string): boolean {
  const { locale, pathname: normalizedPath } = getLocalizedPathInfo(pathname);

  if (!isIndexableLocalizedPath(pathname)) {
    return false;
  }

  if (!locale) {
    return false;
  }

  return isLocaleIndexableForPath(locale, normalizedPath);
}

export function buildLocalizedAlternates(
  pathname: string,
  localeList: readonly (typeof locales)[number][] = getIndexableLocalesForPath(pathname),
  fallbackLocale: (typeof locales)[number] = defaultLocale,
): Record<string, string> {
  const alternates = Object.fromEntries(
    localeList.map((locale) => [locale, toAbsoluteLocalizedUrl(locale, pathname)]),
  );

  return {
    ...alternates,
    'x-default': toAbsoluteLocalizedUrl(fallbackLocale, pathname),
  };
}
