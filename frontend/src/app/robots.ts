import type { MetadataRoute } from 'next';
import { locales } from '@/i18n/config';
import {
  NOINDEX_EXACT_PATHS,
  NOINDEX_PATH_PREFIXES,
  SITE_URL,
} from '@/shared/lib/seo-route-policy';

function buildDisallowPaths(): string[] {
  const disallowPaths = new Set<string>();

  for (const path of NOINDEX_PATH_PREFIXES) {
    disallowPaths.add(path);

    for (const locale of locales) {
      disallowPaths.add(`/${locale}${path}`);
    }
  }

  for (const path of NOINDEX_EXACT_PATHS) {
    disallowPaths.add(path);

    for (const locale of locales) {
      disallowPaths.add(`/${locale}${path}`);
    }
  }

  return [...disallowPaths];
}

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: buildDisallowPaths(),
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
