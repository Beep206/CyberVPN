import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const MESSAGING_PAGE_CONFIG = {
  inbox: {
    canonicalPath: '/messaging',
    descriptionKey: 'inbox.description',
    titleKey: 'inbox.metaTitle',
  },
  detail: {
    canonicalPath: '/messaging',
    descriptionKey: 'inbox.description',
    titleKey: 'inbox.metaTitle',
  },
} as const;

export type MessagingPageKey = keyof typeof MESSAGING_PAGE_CONFIG;

export async function getMessagingPageMetadata(locale: string, page: MessagingPageKey) {
  const t = await getCachedTranslations(locale, 'Messaging');
  const config = MESSAGING_PAGE_CONFIG[page];

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
