import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const SECURITY_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/security',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  sessions: {
    canonicalPath: '/security/sessions',
    titleKey: 'sessions.metaTitle',
    descriptionKey: 'sessions.description',
  },
  twoFactor: {
    canonicalPath: '/security/two-factor',
    titleKey: 'twoFactor.metaTitle',
    descriptionKey: 'twoFactor.description',
  },
  antiPhishing: {
    canonicalPath: '/security/anti-phishing',
    titleKey: 'antiPhishing.metaTitle',
    descriptionKey: 'antiPhishing.description',
  },
  posture: {
    canonicalPath: '/security/posture',
    titleKey: 'posture.metaTitle',
    descriptionKey: 'posture.description',
  },
} as const;

export type SecurityPageKey = keyof typeof SECURITY_PAGE_CONFIG;

export async function getSecurityPageMetadata(locale: string, page: SecurityPageKey) {
  const t = await getCachedTranslations(locale, 'AdminSecurity');
  const config = SECURITY_PAGE_CONFIG[page];

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
