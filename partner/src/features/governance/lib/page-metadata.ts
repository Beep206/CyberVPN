import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const GOVERNANCE_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/governance',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  auditLog: {
    canonicalPath: '/governance/audit-log',
    titleKey: 'auditLog.metaTitle',
    descriptionKey: 'auditLog.description',
  },
  webhookLog: {
    canonicalPath: '/governance/webhook-log',
    titleKey: 'webhookLog.metaTitle',
    descriptionKey: 'webhookLog.description',
  },
  adminInvites: {
    canonicalPath: '/governance/admin-invites',
    titleKey: 'adminInvites.metaTitle',
    descriptionKey: 'adminInvites.description',
  },
  policy: {
    canonicalPath: '/governance/policy',
    titleKey: 'policy.metaTitle',
    descriptionKey: 'policy.description',
  },
} as const;

export type GovernancePageKey = keyof typeof GOVERNANCE_PAGE_CONFIG;

export async function getGovernancePageMetadata(
  locale: string,
  page: GovernancePageKey,
) {
  const t = await getCachedTranslations(locale, 'Governance');
  const config = GOVERNANCE_PAGE_CONFIG[page];

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
