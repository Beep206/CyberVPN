import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const GROWTH_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/growth',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  campaigns: {
    canonicalPath: '/growth/campaigns',
    titleKey: 'campaigns.metaTitle',
    descriptionKey: 'campaigns.description',
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
  giftCodes: {
    canonicalPath: '/growth/gift-codes',
    titleKey: 'giftCodes.metaTitle',
    descriptionKey: 'giftCodes.description',
  },
  partners: {
    canonicalPath: '/growth/partners',
    titleKey: 'partners.metaTitle',
    descriptionKey: 'partners.description',
  },
  reporting: {
    canonicalPath: '/growth/reporting',
    titleKey: 'overview.reporting.title',
    descriptionKey: 'overview.reporting.description',
  },
  notifications: {
    canonicalPath: '/growth/notifications',
    titleKey: 'overview.deliveryOpsTitle',
    descriptionKey: 'overview.deliveryOpsDescription',
  },
  rules: {
    canonicalPath: '/growth/rules',
    titleKey: 'rules.metaTitle',
    descriptionKey: 'rules.description',
  },
  siteMode: {
    canonicalPath: '/growth/site-mode',
    titleKey: 'siteMode.metaTitle',
    descriptionKey: 'siteMode.description',
  },
  fx: {
    canonicalPath: '/growth/fx',
    titleKey: 'fx.metaTitle',
    descriptionKey: 'fx.description',
  },
  privateAccess: {
    canonicalPath: '/growth/private-access',
    titleKey: 'privateAccess.metaTitle',
    descriptionKey: 'privateAccess.description',
  },
  onboarding: {
    canonicalPath: '/growth/onboarding',
    titleKey: 'onboarding.metaTitle',
    descriptionKey: 'onboarding.description',
  },
  risk: {
    canonicalPath: '/growth/risk',
    titleKey: 'referrals.metaTitle',
    descriptionKey: 'referrals.description',
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
