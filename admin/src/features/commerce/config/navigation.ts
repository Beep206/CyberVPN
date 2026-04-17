export const COMMERCE_NAV_ITEMS = [
  {
    href: '/commerce',
    labelKey: 'nav.overview',
  },
  {
    href: '/commerce/plans',
    labelKey: 'nav.plans',
  },
  {
    href: '/commerce/addons',
    labelKey: 'nav.addons',
  },
  {
    href: '/commerce/subscription-templates',
    labelKey: 'nav.subscriptionTemplates',
  },
  {
    href: '/commerce/payments',
    labelKey: 'nav.payments',
  },
  {
    href: '/commerce/wallets',
    labelKey: 'nav.wallets',
  },
  {
    href: '/commerce/withdrawals',
    labelKey: 'nav.withdrawals',
  },
] as const;

export type CommerceNavHref = (typeof COMMERCE_NAV_ITEMS)[number]['href'];
