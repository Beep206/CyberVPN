import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const INFRASTRUCTURE_PAGE_CONFIG = {
  overview: {
    canonicalPath: '/infrastructure',
    titleKey: 'overview.metaTitle',
    descriptionKey: 'overview.description',
  },
  servers: {
    canonicalPath: '/infrastructure/servers',
    titleKey: 'servers.metaTitle',
    descriptionKey: 'servers.description',
  },
  hosts: {
    canonicalPath: '/infrastructure/hosts',
    titleKey: 'hosts.metaTitle',
    descriptionKey: 'hosts.description',
  },
  configProfiles: {
    canonicalPath: '/infrastructure/config-profiles',
    titleKey: 'configProfiles.metaTitle',
    descriptionKey: 'configProfiles.description',
  },
  nodePlugins: {
    canonicalPath: '/infrastructure/node-plugins',
    titleKey: 'nodePlugins.metaTitle',
    descriptionKey: 'nodePlugins.description',
  },
  xray: {
    canonicalPath: '/infrastructure/xray',
    titleKey: 'xray.metaTitle',
    descriptionKey: 'xray.description',
  },
  helix: {
    canonicalPath: '/infrastructure/helix',
    titleKey: 'helix.metaTitle',
    descriptionKey: 'helix.description',
  },
  inbounds: {
    canonicalPath: '/infrastructure/inbounds',
    titleKey: 'inbounds.metaTitle',
    descriptionKey: 'inbounds.description',
  },
  squads: {
    canonicalPath: '/infrastructure/squads',
    titleKey: 'squads.metaTitle',
    descriptionKey: 'squads.description',
  },
  snippets: {
    canonicalPath: '/infrastructure/snippets',
    titleKey: 'snippets.metaTitle',
    descriptionKey: 'snippets.description',
  },
} as const;

export type InfrastructurePageKey = keyof typeof INFRASTRUCTURE_PAGE_CONFIG;

export async function getInfrastructurePageMetadata(
  locale: string,
  page: InfrastructurePageKey,
) {
  const t = await getCachedTranslations(locale, 'Infrastructure');
  const config = INFRASTRUCTURE_PAGE_CONFIG[page];

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
