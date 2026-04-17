import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const COMMERCE_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/commerce',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  plans: {
    canonicalPath: '/commerce/plans',
    titleKey: 'plans.metaTitle',
    descriptionKey: 'plans.description',
  },
  addons: {
    canonicalPath: '/commerce/addons',
    titleKey: 'addons.metaTitle',
    descriptionKey: 'addons.description',
  },
  subscriptionTemplates: {
    canonicalPath: '/commerce/subscription-templates',
    titleKey: 'subscriptionTemplates.metaTitle',
    descriptionKey: 'subscriptionTemplates.description',
  },
  payments: {
    canonicalPath: '/commerce/payments',
    titleKey: 'payments.metaTitle',
    descriptionKey: 'payments.description',
  },
  wallets: {
    canonicalPath: '/commerce/wallets',
    titleKey: 'wallets.metaTitle',
    descriptionKey: 'wallets.description',
  },
  withdrawals: {
    canonicalPath: '/commerce/withdrawals',
    titleKey: 'withdrawals.metaTitle',
    descriptionKey: 'withdrawals.description',
  },
} as const;

export type CommercePageKey = keyof typeof COMMERCE_PAGE_CONFIG;

export async function getCommercePageMetadata(
  locale: string,
  page: CommercePageKey,
) {
  const t = await getCachedTranslations(locale, 'Commerce');
  const config = COMMERCE_PAGE_CONFIG[page];

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
