import {
  defaultLocale,
  locales,
  mediumPriorityLocales,
} from '@/i18n/config';
import { seoPriorityMarketLocales } from '@/content/seo/market-localization';
import { seoDetailLocales } from '@/content/seo/market-detail-localization';

type Locale = (typeof locales)[number];

export type LocaleRolloutTier = 'tier1' | 'tier2' | 'tier3';

export const EXPANDED_CONTENT_HUB_PATHS = [
  '/audits',
  '/compare',
  '/devices',
  '/guides',
  '/trust',
] as const;
export const EXPANDED_CONTENT_DETAIL_PREFIXES = [
  '/compare/',
  '/devices/',
  '/guides/',
] as const;

export const CORE_SEO_LOCALES = [...seoPriorityMarketLocales] as const;
export const EXPANDED_CONTENT_DETAIL_LOCALES = [...seoDetailLocales] as const;

function normalizePathname(pathname: string): string {
  if (!pathname) {
    return '/';
  }

  const normalized = pathname.trim().startsWith('/') ? pathname.trim() : `/${pathname.trim()}`;

  if (normalized === '/') {
    return '/';
  }

  return normalized.replace(/\/+$/, '');
}

export function getLocaleRolloutTier(locale: string): LocaleRolloutTier {
  if (seoPriorityMarketLocales.includes(locale as (typeof seoPriorityMarketLocales)[number])) {
    return 'tier1';
  }

  if (mediumPriorityLocales.includes(locale as (typeof mediumPriorityLocales)[number])) {
    return 'tier2';
  }

  return 'tier3';
}

export function isExpandedContentPath(pathname: string): boolean {
  const normalizedPath = normalizePathname(pathname);

  if (
    EXPANDED_CONTENT_HUB_PATHS.includes(
      normalizedPath as (typeof EXPANDED_CONTENT_HUB_PATHS)[number],
    )
  ) {
    return true;
  }

  return EXPANDED_CONTENT_DETAIL_PREFIXES.some(
    (prefix) => normalizedPath.startsWith(prefix),
  );
}

export function isExpandedContentHubPath(pathname: string): boolean {
  return EXPANDED_CONTENT_HUB_PATHS.includes(
    normalizePathname(pathname) as (typeof EXPANDED_CONTENT_HUB_PATHS)[number],
  );
}

export function isExpandedContentDetailPath(pathname: string): boolean {
  const normalizedPath = normalizePathname(pathname);

  return EXPANDED_CONTENT_DETAIL_PREFIXES.some((prefix) => normalizedPath.startsWith(prefix));
}

export function getIndexableLocalesForPath(
  pathname: string,
): readonly Locale[] {
  if (isExpandedContentDetailPath(pathname)) {
    return EXPANDED_CONTENT_DETAIL_LOCALES;
  }

  if (isExpandedContentHubPath(pathname)) {
    return CORE_SEO_LOCALES;
  }

  return CORE_SEO_LOCALES;
}

export function isLocaleIndexableForPath(locale: string, pathname: string): boolean {
  return getIndexableLocalesForPath(pathname).includes(locale as Locale);
}

export function getCanonicalLocaleForPath(pathname: string, locale?: string): Locale {
  if (locale && isLocaleIndexableForPath(locale, pathname)) {
    return locale as Locale;
  }

  return getIndexableLocalesForPath(pathname)[0] ?? defaultLocale;
}
