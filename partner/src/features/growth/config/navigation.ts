export const GROWTH_NAV_ITEMS = [
  { href: '/growth', labelKey: 'nav.overview' },
  { href: '/growth/promo-codes', labelKey: 'nav.promoCodes' },
  { href: '/growth/invite-codes', labelKey: 'nav.inviteCodes' },
  { href: '/growth/partners', labelKey: 'nav.partners' },
  { href: '/growth/referrals', labelKey: 'nav.referrals' },
] as const;

export type GrowthNavHref = (typeof GROWTH_NAV_ITEMS)[number]['href'];
