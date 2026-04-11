export const INTEGRATIONS_NAV_ITEMS = [
  { href: '/integrations', labelKey: 'nav.overview' },
  { href: '/integrations/telegram', labelKey: 'nav.telegram' },
  { href: '/integrations/push', labelKey: 'nav.push' },
  { href: '/integrations/realtime', labelKey: 'nav.realtime' },
] as const;

export type IntegrationsNavHref =
  (typeof INTEGRATIONS_NAV_ITEMS)[number]['href'];
