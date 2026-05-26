import type { MetadataRoute } from 'next';
import { locales } from '@/i18n/config';
import {
  NOINDEX_EXACT_PATHS,
  NOINDEX_PATH_PREFIXES,
  SITE_URL,
  toLocalizedPath,
} from '@/shared/lib/seo-route-policy';

function unique(values: string[]): string[] {
  return Array.from(new Set(values));
}

export default function robots(): MetadataRoute.Robots {
  const privatePaths = [
    ...NOINDEX_PATH_PREFIXES,
    ...NOINDEX_EXACT_PATHS,
  ];
  const disallow = unique([
    ...privatePaths,
    ...locales.flatMap((locale) =>
      privatePaths.map((pathname) => toLocalizedPath(locale, pathname)),
    ),
  ]);

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow,
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
