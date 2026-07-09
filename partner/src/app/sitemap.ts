import type { MetadataRoute } from 'next';
import { getIndexableLocalesForPath } from '@/shared/lib/locale-rollout-policy';
import {
  INDEXABLE_MARKETING_PATHS,
  isRolloutIndexableLocalizedPath,
  toAbsoluteLocalizedUrl,
} from '@/shared/lib/seo-route-policy';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const routes = Array.from(new Set([
    ...INDEXABLE_MARKETING_PATHS,
  ]));

  return routes.flatMap((route) =>
    getIndexableLocalesForPath(route)
      .filter((locale) => isRolloutIndexableLocalizedPath(`/${locale}${route === '/' ? '' : route}`))
      .map((locale) => ({
        url: toAbsoluteLocalizedUrl(locale, route),
        changeFrequency: 'weekly' as const,
        priority: route === '/' ? 1 : 0.7,
      })),
  );
}
