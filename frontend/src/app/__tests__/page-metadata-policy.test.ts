import { describe, expect, it, vi } from 'vitest';
import { generateMetadata as generateMarketingHomeMetadata } from '../[locale]/(marketing)/page';
import { generateMetadata as generatePricingMetadata } from '../[locale]/(marketing)/pricing/page';
import { generateMetadata as generateHelpMetadata } from '../[locale]/(marketing)/help/page';
import { generateMetadata as generateAuthMetadata } from '../[locale]/(auth)/layout';
import { generateMetadata as generateDashboardMetadata } from '../[locale]/(dashboard)/layout';
import { generateMetadata as generateMiniAppMetadata } from '../[locale]/miniapp/layout';
import { generateMetadata as generateTestAnimationMetadata } from '../[locale]/test-animation/layout';
import { generateMetadata as generateTestErrorMetadata } from '../[locale]/test-error/layout';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async (input?: string | { namespace?: string }) => {
    const namespace =
      typeof input === 'string' ? input : input?.namespace ?? 'unknown';

    return (key: string) => `${namespace}.${key}`;
  }),
}));

vi.mock('@/i18n/server', () => ({
  getCachedTranslations: vi.fn(async (_locale: string, namespace?: string) => {
    return (key: string) => `${namespace ?? 'unknown'}.${key}`;
  }),
  getScopedMessages: vi.fn(async () => ({})),
  setRequestLocale: vi.fn(),
  getFormatter: vi.fn(),
  getLocale: vi.fn(async () => 'en-EN'),
  getMessages: vi.fn(async () => ({})),
  getNow: vi.fn(async () => new Date('2026-01-01T00:00:00Z')),
  getTimeZone: vi.fn(async () => 'UTC'),
}));

vi.mock('next/cache', () => ({
  cacheLife: vi.fn(),
  cacheTag: vi.fn(),
}));

describe('page metadata policy', () => {
  it('keeps core marketing routes indexable with localized canonical paths and route-specific copy', async () => {
    const [homeMetadata, pricingMetadata, helpMetadata] = await Promise.all([
      generateMarketingHomeMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
      generatePricingMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
      generateHelpMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
    ]);

    expect(homeMetadata.alternates?.canonical).toBe('https://vpn.ozoxy.ru/en-EN');
    expect(pricingMetadata.alternates?.canonical).toBe(
      'https://vpn.ozoxy.ru/en-EN/pricing',
    );
    expect(helpMetadata.alternates?.canonical).toBe('https://vpn.ozoxy.ru/en-EN/help');

    expect(homeMetadata.title).toBe('Landing.hero.title Landing.hero.titleHighlight | CyberVPN');
    expect(pricingMetadata.title).toBe('Pricing.title | CyberVPN');
    expect(helpMetadata.description).toBe('HelpCenter.meta_description');

    expect(homeMetadata.robots).toBeUndefined();
    expect(pricingMetadata.robots).toBeUndefined();
    expect(helpMetadata.robots).toBeUndefined();
  });

  it('marks auth, dashboard, miniapp, and test routes as noindex without public alternates', async () => {
    const metadataEntries = await Promise.all([
      generateAuthMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
      generateDashboardMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
      generateMiniAppMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
      generateTestAnimationMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
      generateTestErrorMetadata({ params: Promise.resolve({ locale: 'en-EN' }) }),
    ]);

    for (const metadata of metadataEntries) {
      expect(metadata.robots).toMatchObject({
        index: false,
        follow: false,
        googleBot: {
          index: false,
          follow: false,
        },
      });
      expect(metadata.alternates).toEqual({});
    }
  });
});
