import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const SUPPORT_PAGE_CONFIG = {
  inbox: {
    canonicalPath: '/support',
    descriptionKey: 'inbox.description',
    titleKey: 'inbox.metaTitle',
  },
  detail: {
    canonicalPath: '/support',
    descriptionKey: 'inbox.description',
    titleKey: 'inbox.metaTitle',
  },
} as const;

export type SupportPageKey = keyof typeof SUPPORT_PAGE_CONFIG;

export async function getSupportPageMetadata(locale: string, page: SupportPageKey) {
  const t = await getCachedTranslations(locale, 'Support');
  const config = SUPPORT_PAGE_CONFIG[page];

  return withSiteMetadata(
    {
      description: t(config.descriptionKey),
      title: t(config.titleKey),
    },
    {
      canonicalPath: config.canonicalPath,
      locale,
      routeType: 'private',
    },
  );
}
