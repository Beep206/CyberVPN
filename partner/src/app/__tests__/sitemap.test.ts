import { describe, expect, it, vi } from 'vitest';
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
  it('includes only storefront public routes on the canonical domain', async () => {
    const entries = await sitemap();
    const urls = new Set(entries.map((entry) => entry.url));
    const expectedCount = INDEXABLE_MARKETING_PATHS.reduce(
      (count, route) => count + getIndexableLocalesForPath(route).length,
      0,
    );

    expect(entries).toHaveLength(expectedCount);
    expect(entries.every((entry) => entry.url.startsWith(SITE_URL))).toBe(true);

    const expectedPublicUrls = [
      `${SITE_URL}/en-EN`,
      `${SITE_URL}/ru-RU`,
      `${SITE_URL}/en-EN/checkout`,
      `${SITE_URL}/ru-RU/checkout`,
      `${SITE_URL}/en-EN/legal-docs`,
      `${SITE_URL}/ru-RU/support`,
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
        `${SITE_URL}/en-EN/pricing`,
        `${SITE_URL}/ru-RU/guides`,
        `${SITE_URL}/ru-RU/guides/how-to-bypass-dpi-with-vless-reality`,
        `${SITE_URL}/ru-RU/devices/android-vpn-setup`,
        `${SITE_URL}/en-EN/trust`,
        `${SITE_URL}/en-EN/audits`,
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
