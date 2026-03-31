import type { Metadata } from 'next';
import { defaultLocale, locales, rtlLocales } from '@/i18n/config';
import {
  getCanonicalLocaleForPath,
  getIndexableLocalesForPath,
  isLocaleIndexableForPath,
} from '@/shared/lib/locale-rollout-policy';
import {
  SITE_URL,
  buildLocalizedAlternates,
  isIndexableLocalizedPath,
  toAbsoluteLocalizedUrl,
  toLocalizedPath,
} from '@/shared/lib/seo-route-policy';

export { SITE_URL } from '@/shared/lib/seo-route-policy';

type Locale = (typeof locales)[number];
type TextDirection = 'ltr' | 'rtl';

export type SiteRouteType = 'public' | 'private';

export type SiteMetadataOptions = {
  locale?: string;
  canonicalPath?: string;
  routeType?: SiteRouteType;
};

export type HtmlLanguageAttributes = {
  lang: Locale;
  dir: TextDirection;
};

const NOINDEX_ROBOTS: NonNullable<Metadata['robots']> = {
  index: false,
  follow: false,
  googleBot: {
    index: false,
    follow: false,
    noimageindex: true,
    'max-image-preview': 'none',
    'max-snippet': 0,
    'max-video-preview': 0,
  },
};

function isKnownLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}

function resolveLocale(locale?: string): Locale {
  if (locale && isKnownLocale(locale)) {
    return locale;
  }

  return defaultLocale;
}

function resolveRouteType(
  locale: Locale,
  canonicalPath?: string,
  routeType?: SiteRouteType,
): SiteRouteType | undefined {
  if (routeType) {
    return routeType;
  }

  if (!canonicalPath) {
    return undefined;
  }

  return isIndexableLocalizedPath(toLocalizedPath(locale, canonicalPath))
    ? 'public'
    : 'private';
}

function buildAlternates(locale: Locale, canonicalPath: string): Metadata['alternates'] {
  return {
    canonical: toAbsoluteLocalizedUrl(locale, canonicalPath),
    languages: buildLocalizedAlternates(canonicalPath, getIndexableLocalesForPath(canonicalPath)),
  };
}

function buildDefaultSocialImage(locale: Locale): string {
  return toAbsoluteLocalizedUrl(locale, '/opengraph-image');
}

export function getHtmlLanguageAttributes(locale?: string): HtmlLanguageAttributes {
  const resolvedLocale = resolveLocale(locale);
  const dir: TextDirection = rtlLocales.includes(resolvedLocale as (typeof rtlLocales)[number])
    ? 'rtl'
    : 'ltr';

  return {
    lang: resolvedLocale,
    dir,
  };
}

export function withSiteMetadata(
  metadata: Metadata,
  options: SiteMetadataOptions = {},
): Metadata {
  const locale = resolveLocale(options.locale);
  const routeType = resolveRouteType(locale, options.canonicalPath, options.routeType);
  const canonicalLocale =
    routeType === 'public' && options.canonicalPath
      ? getCanonicalLocaleForPath(options.canonicalPath, locale)
      : locale;
  const localeIsIndexable =
    routeType === 'public' && options.canonicalPath
      ? isLocaleIndexableForPath(locale, options.canonicalPath)
      : true;
  const canonicalUrl =
    routeType === 'public' && options.canonicalPath
      ? toAbsoluteLocalizedUrl(canonicalLocale, options.canonicalPath)
      : undefined;
  const defaultSocialImage = buildDefaultSocialImage(locale);

  const alternates =
    routeType === 'public' && options.canonicalPath
      ? {
          ...buildAlternates(canonicalLocale, options.canonicalPath),
          ...metadata.alternates,
          languages: {
            ...buildLocalizedAlternates(
              options.canonicalPath,
              getIndexableLocalesForPath(options.canonicalPath),
            ),
            ...metadata.alternates?.languages,
          },
          canonical:
            metadata.alternates?.canonical ??
            toAbsoluteLocalizedUrl(canonicalLocale, options.canonicalPath),
        }
      : metadata.alternates;

  const siteMetadata: Metadata = {
    metadataBase: new URL(SITE_URL),
    ...metadata,
    openGraph: {
      ...metadata.openGraph,
      url: metadata.openGraph?.url ?? canonicalUrl,
      siteName: metadata.openGraph?.siteName ?? 'CyberVPN',
      images: metadata.openGraph?.images ?? [
        {
          url: defaultSocialImage,
          width: 1200,
          height: 630,
          alt: 'CyberVPN - Advanced VPN Service',
        },
      ],
    },
    twitter: {
      ...metadata.twitter,
      images: metadata.twitter?.images ?? [defaultSocialImage],
    },
  };

  if (alternates) {
    siteMetadata.alternates = alternates;
  }

  if (routeType === 'private') {
    siteMetadata.alternates = {};
    siteMetadata.robots = NOINDEX_ROBOTS;
  } else if (!localeIsIndexable) {
    siteMetadata.robots = NOINDEX_ROBOTS;
  } else if (metadata.robots) {
    siteMetadata.robots = metadata.robots;
  }

  return siteMetadata;
}
