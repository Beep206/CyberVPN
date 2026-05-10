import type { MetadataRoute } from 'next';
import { locales } from '@/i18n/config';
import {
  NOINDEX_EXACT_PATHS,
  NOINDEX_PATH_PREFIXES,
  SITE_URL,
} from '@/shared/lib/seo-route-policy';

export default function robots(): MetadataRoute.Robots {
  const disallow = [
    ...NOINDEX_PATH_PREFIXES,
    ...NOINDEX_EXACT_PATHS,
    ...locales.flatMap((locale) => [
      ...NOINDEX_PATH_PREFIXES.map((path) => `/${locale}${path}`),
      ...NOINDEX_EXACT_PATHS.map((path) => `/${locale}${path}`),
    ]),
  ];

  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow,
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
