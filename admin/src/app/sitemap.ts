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

const SITEMAP_LAST_MODIFIED = new Date('2026-05-10T00:00:00.000Z');

function priorityForPath(pathname: string): number {
  if (pathname === '/') return 1;
  if (pathname === '/pricing') return 0.95;
  if (pathname === '/help' || pathname === '/status') return 0.9;
  if (pathname.startsWith('/guides/') || pathname.startsWith('/compare/')) return 0.75;
  if (pathname.startsWith('/devices/')) return 0.7;
  return 0.8;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [guideEntries, comparisonEntries, deviceEntries] = await Promise.all([
    getGuideEntries(),
    getComparisonEntries(),
    getDeviceEntries(),
  ]);

  const paths = [
    ...INDEXABLE_MARKETING_PATHS,
    ...guideEntries.map((entry) => entry.path),
    ...comparisonEntries.map((entry) => entry.path),
    ...deviceEntries.map((entry) => entry.path),
  ];

  const uniquePaths = [...new Set(paths)];

  return uniquePaths.flatMap((pathname) =>
    getIndexableLocalesForPath(pathname)
      .map((locale) => ({
        url: toAbsoluteLocalizedUrl(locale, pathname),
        lastModified: SITEMAP_LAST_MODIFIED,
        changeFrequency: 'weekly' as const,
        priority: priorityForPath(pathname),
      }))
      .filter((entry) => isRolloutIndexableLocalizedPath(new URL(entry.url).pathname)),
  );
}
