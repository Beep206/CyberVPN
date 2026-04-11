import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const CUSTOMERS_PAGE_CONFIG = {
  directory: {
    canonicalPath: '/customers',
    titleKey: 'directory.metaTitle',
    descriptionKey: 'directory.description',
  },
  detail: {
    canonicalPath: '/customers',
    titleKey: 'detail.metaTitle',
    descriptionKey: 'detail.description',
  },
} as const;

export type CustomersPageKey = keyof typeof CUSTOMERS_PAGE_CONFIG;

export async function getCustomersPageMetadata(locale: string, page: CustomersPageKey) {
  const t = await getCachedTranslations(locale, 'Customers');
  const config = CUSTOMERS_PAGE_CONFIG[page];

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
