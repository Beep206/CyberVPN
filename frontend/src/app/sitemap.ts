import type { MetadataRoute } from 'next';
import { getComparisonEntries } from '@/content/seo/comparisons';
import { getDeviceEntries } from '@/content/seo/devices';
import { getGuideEntries } from '@/content/seo/guides';
import { getIndexableLocalesForPath } from '@/shared/lib/locale-rollout-policy';
import {
  INDEXABLE_MARKETING_PATHS,
  SITE_URL,
  toLocalizedPath,
} from '@/shared/lib/seo-route-policy';

type SitemapRouteDefinition = {
  path: string;
  lastModified?: string;
  priority: number;
};

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const lastModified = new Date();
  const [guideEntries, comparisonEntries, deviceEntries] = await Promise.all([
    getGuideEntries(),
    getComparisonEntries(),
    getDeviceEntries(),
  ]);

  const routes: SitemapRouteDefinition[] = [
    ...INDEXABLE_MARKETING_PATHS.map((route) => ({
      path: route,
      priority: route === '/' ? 1.0 : 0.8,
    })),
    ...guideEntries.map((entry) => ({
      path: entry.path,
      lastModified: entry.updatedAt,
      priority: 0.76,
    })),
    ...comparisonEntries.map((entry) => ({
      path: entry.path,
      lastModified: entry.updatedAt,
      priority: 0.76,
    })),
    ...deviceEntries.map((entry) => ({
      path: entry.path,
      lastModified: entry.updatedAt,
      priority: 0.76,
    })),
  ];

  return routes.flatMap((route) =>
    getIndexableLocalesForPath(route.path).map((locale) => ({
      url: new URL(toLocalizedPath(locale, route.path), SITE_URL).toString(),
      lastModified: route.lastModified ? new Date(route.lastModified) : lastModified,
      changeFrequency: 'weekly',
      priority: route.priority,
    })),
  );
}
