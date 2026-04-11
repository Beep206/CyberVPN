import { describe, expect, it, vi } from 'vitest';
import { getComparisonEntries } from '@/content/seo/comparisons';
import { getDeviceEntries } from '@/content/seo/devices';
import { getGuideEntries } from '@/content/seo/guides';
import { getIndexableLocalesForPath } from '@/shared/lib/locale-rollout-policy';
import sitemap from '../sitemap';
import {
  INDEXABLE_MARKETING_PATHS,
  SITE_URL,
  isRolloutIndexableLocalizedPath,
} from '@/shared/lib/seo-route-policy';

vi.mock('next/cache', () => ({
  cacheLife: vi.fn(),
  cacheTag: vi.fn(),
}));

describe('sitemap', () => {
  it('includes only rollout-eligible public routes on the canonical domain', async () => {
    const [entries, guideEntries, comparisonEntries, deviceEntries] = await Promise.all([
      sitemap(),
      getGuideEntries(),
      getComparisonEntries(),
      getDeviceEntries(),
    ]);
    const urls = new Set(entries.map((entry) => entry.url));
    const allIndexedRoutes = [
      ...INDEXABLE_MARKETING_PATHS,
      ...guideEntries.map((entry) => entry.path),
      ...comparisonEntries.map((entry) => entry.path),
      ...deviceEntries.map((entry) => entry.path),
    ];
    const expectedCount = allIndexedRoutes.reduce(
      (count, route) => count + getIndexableLocalesForPath(route).length,
      0,
    );

    expect(entries).toHaveLength(expectedCount);
    expect(entries.every((entry) => entry.url.startsWith(SITE_URL))).toBe(true);

    const expectedPublicUrls = [
      `${SITE_URL}/en-EN`,
      `${SITE_URL}/ru-RU/pricing`,
      `${SITE_URL}/zh-CN/help`,
      `${SITE_URL}/ru-RU/guides`,
      `${SITE_URL}/zh-CN/trust`,
      `${SITE_URL}/ru-RU/guides/how-to-bypass-dpi-with-vless-reality`,
      `${SITE_URL}/zh-CN/compare/vless-reality-vs-wireguard`,
      `${SITE_URL}/ru-RU/devices/android-vpn-setup`,
      `${SITE_URL}/hi-IN/guides/how-to-bypass-dpi-with-vless-reality`,
      `${SITE_URL}/ja-JP/devices/android-vpn-setup`,
      `${SITE_URL}/en-EN/trust`,
      `${SITE_URL}/en-EN/audits`,
    ];

    for (const expectedUrl of expectedPublicUrls) {
      expect(urls.has(expectedUrl)).toBe(true);
    }

    expect(Array.from(urls)).not.toEqual(
      expect.arrayContaining([
        `${SITE_URL}/en-EN/dashboard`,
        `${SITE_URL}/en-EN/miniapp`,
        `${SITE_URL}/en-EN/login`,
        `${SITE_URL}/en-EN/oauth/callback`,
        `${SITE_URL}/en-EN/test-animation`,
        `${SITE_URL}/en-EN/test-error`,
        `${SITE_URL}/fa-IR/pricing`,
        `${SITE_URL}/fa-IR/guides`,
        `${SITE_URL}/fa-IR/guides/how-to-bypass-dpi-with-vless-reality`,
        `${SITE_URL}/ar-SA/devices/android-vpn-setup`,
        `${SITE_URL}/fa-IR/compare/vless-reality-vs-wireguard`,
      ]),
    );

    expect(
      entries.every((entry) => isRolloutIndexableLocalizedPath(new URL(entry.url).pathname)),
    ).toBe(true);
  });
});
