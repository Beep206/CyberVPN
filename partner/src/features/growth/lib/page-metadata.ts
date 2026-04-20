import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const GROWTH_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/growth',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  promoCodes: {
    canonicalPath: '/growth/promo-codes',
    titleKey: 'promoCodes.metaTitle',
    descriptionKey: 'promoCodes.description',
  },
  inviteCodes: {
    canonicalPath: '/growth/invite-codes',
    titleKey: 'inviteCodes.metaTitle',
    descriptionKey: 'inviteCodes.description',
  },
  partners: {
    canonicalPath: '/growth/partners',
    titleKey: 'partners.metaTitle',
    descriptionKey: 'partners.description',
  },
  referrals: {
    canonicalPath: '/growth/referrals',
    titleKey: 'referrals.metaTitle',
    descriptionKey: 'referrals.description',
  },
} as const;

export type GrowthPageKey = keyof typeof GROWTH_PAGE_CONFIG;

export async function getGrowthPageMetadata(locale: string, page: GrowthPageKey) {
  const t = await getCachedTranslations(locale, 'Growth');
  const config = GROWTH_PAGE_CONFIG[page];

  return withSiteMetadata(
    {
      title: t(config.titleKey),
      description: t(config.descriptionKey),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: config.canonicalPath,
    },
  );
}
