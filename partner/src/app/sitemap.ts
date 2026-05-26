import type { MetadataRoute } from 'next';
import { getComparisonEntries } from '@/content/seo/comparisons';
import { getDeviceEntries } from '@/content/seo/devices';
import { getGuideEntries } from '@/content/seo/guides';
import { getIndexableLocalesForPath } from '@/shared/lib/locale-rollout-policy';
import {
  INDEXABLE_MARKETING_PATHS,
  isRolloutIndexableLocalizedPath,
  toAbsoluteLocalizedUrl,
} from '@/shared/lib/seo-route-policy';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [guideEntries, comparisonEntries, deviceEntries] = await Promise.all([
    getGuideEntries(),
    getComparisonEntries(),
    getDeviceEntries(),
  ]);
  const routes = Array.from(new Set([
    ...INDEXABLE_MARKETING_PATHS,
    ...guideEntries.map((entry) => entry.path),
    ...comparisonEntries.map((entry) => entry.path),
    ...deviceEntries.map((entry) => entry.path),
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
