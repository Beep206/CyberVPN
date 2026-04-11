import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const INTEGRATIONS_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/integrations',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  telegram: {
    canonicalPath: '/integrations/telegram',
    titleKey: 'telegram.metaTitle',
    descriptionKey: 'telegram.description',
  },
  push: {
    canonicalPath: '/integrations/push',
    titleKey: 'push.metaTitle',
    descriptionKey: 'push.description',
  },
  realtime: {
    canonicalPath: '/integrations/realtime',
    titleKey: 'realtime.metaTitle',
    descriptionKey: 'realtime.description',
  },
} as const;

export type IntegrationsPageKey = keyof typeof INTEGRATIONS_PAGE_CONFIG;

export async function getIntegrationsPageMetadata(
  locale: string,
  page: IntegrationsPageKey,
) {
  const t = await getCachedTranslations(locale, 'Integrations');
  const config = INTEGRATIONS_PAGE_CONFIG[page];

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
