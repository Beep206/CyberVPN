export const INFRASTRUCTURE_NAV_ITEMS = [
  { href: '/infrastructure', labelKey: 'nav.overview' },
  { href: '/infrastructure/servers', labelKey: 'nav.servers' },
  { href: '/infrastructure/hosts', labelKey: 'nav.hosts' },
  { href: '/infrastructure/config-profiles', labelKey: 'nav.configProfiles' },
  { href: '/infrastructure/node-plugins', labelKey: 'nav.nodePlugins' },
  { href: '/infrastructure/xray', labelKey: 'nav.xray' },
  { href: '/infrastructure/helix', labelKey: 'nav.helix' },
  { href: '/infrastructure/inbounds', labelKey: 'nav.inbounds' },
  { href: '/infrastructure/squads', labelKey: 'nav.squads' },
  { href: '/infrastructure/snippets', labelKey: 'nav.snippets' },
] as const;

export type InfrastructureNavHref =
  (typeof INFRASTRUCTURE_NAV_ITEMS)[number]['href'];
